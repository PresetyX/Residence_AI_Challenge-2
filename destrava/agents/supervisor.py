"""Supervisor do Destrava: visualiza e cria eventos (sem RAG)."""

from datetime import datetime
from typing import Callable, Literal

from pydantic import BaseModel, ValidationError

from destrava.agents.visualizar import AgenteVisualizar
from destrava.agents.criar import AgenteCriar

from destrava.core import config
from destrava.core.llm_client import ErroLLM, extrair_json, perguntar
from destrava.core.models import PedidoVisualizacao, PedidoCriacao
from destrava.prompts.supervisor import PROMPT_SUPERVISOR


class InterpretacaoSupervisor(BaseModel):
    acao: Literal["visualizar", "criar", "planejar", "esclarecer", "fora_escopo"]
    dados: dict | None = None
    pergunta: str | None = None


def _formatar_horarios(resposta: dict) -> str:
    """Transforma os horários livres em texto."""
    dados = resposta["dados"]
    livres = dados["livres"]

    minutos = round(float(dados["total_minutos_livres"]))
    horas, resto = divmod(minutos, 60)

    if not livres:
        return "Não encontrei horários livres no período consultado."

    linhas = [f"Você tem {horas}h{resto:02d}min livres no período consultado:"]

    for bloco in livres:
        inicio = datetime.fromisoformat(bloco["inicio"])
        fim = datetime.fromisoformat(bloco["fim"])

        if inicio.date() == fim.date():
            linhas.append(
                f"- {inicio:%d/%m}, das {inicio:%H:%M} às {fim:%H:%M}"
            )
        else:
            linhas.append(
                f"- {inicio:%d/%m %H:%M} até {fim:%d/%m %H:%M}"
            )

    return "\n".join(linhas)


class AgenteSupervisor:
    def __init__(
        self,
        visualizador: AgenteVisualizar | None = None,
        criador: AgenteCriar | None = None,
        consultar_llm: Callable[[str], str] | None = None,
    ):
        self.visualizador = visualizador if visualizador is not None else AgenteVisualizar()
        self.criador = criador if criador is not None else AgenteCriar()
        self.consultar_llm = consultar_llm if consultar_llm is not None else perguntar

        # Guarda apenas o evento que está aguardando confirmação.
        self.evento_pendente = None

    def verificar_disponibilidade(self, evento: dict) -> bool:
        """Confere se o horário inteiro aparece como livre."""

        try:
            resposta = self.visualizador.executar_json({
                "inicio": evento["inicio"],
                "fim": evento["fim"]
            })

            if resposta.get("status") != "sucesso":
                return False

            inicio = datetime.fromisoformat(evento["inicio"])
            fim = datetime.fromisoformat(evento["fim"])

            for bloco in resposta["dados"]["livres"]:
                livre_inicio = datetime.fromisoformat(bloco["inicio"])
                livre_fim = datetime.fromisoformat(bloco["fim"])

                if livre_inicio <= inicio and livre_fim >= fim:
                    return True

        except (KeyError, TypeError, ValueError, AttributeError):
            return False
        except Exception:
            return False

        return False

    def executar(self, pedido: str) -> dict:
        """Recebe o pedido do estudante e coordena os agentes."""

        if not isinstance(pedido, str) or not pedido.strip():
            return {
                "status": "erro",
                "acao": "esclarecer",
                "mensagem": "Descreva o que deseja fazer."
            }

        pedido = pedido.strip()

        # 1. Verifica se existe um evento aguardando confirmação.
        if self.evento_pendente is not None:

            if pedido.lower() in ("não", "nao"):
                self.evento_pendente = None
                return {
                    "status": "cancelado",
                    "acao": "criar",
                    "mensagem": "Criação cancelada. Nenhum evento foi criado."
                }

            if pedido.lower() == "sim":
                evento = self.evento_pendente
                self.evento_pendente = None

                # Consulta novamente para evitar usar disponibilidade antiga.
                if not self.verificar_disponibilidade(evento):
                    return {
                        "status": "erro",
                        "acao": "criar",
                        "mensagem": "Não consegui confirmar que esse horário continua livre. Nenhum evento foi criado."
                    }

                try:
                    resposta = self.criador.executar_json(evento)
                except Exception as erro:
                    return {
                        "status": "erro",
                        "acao": "criar",
                        "mensagem": f"Falha ao criar evento: {erro}"
                    }

                if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
                    erro = resposta.get("erro") if isinstance(resposta, dict) else None
                    mensagem = erro.get("mensagem") if isinstance(erro, dict) else "Falha desconhecida."
                    return {
                        "status": "erro",
                        "acao": "criar",
                        "mensagem": f"Não foi possível criar o evento: {mensagem}"
                    }

                criado = resposta["dados"]["evento"]

                return {
                    "status": "sucesso",
                    "acao": "criar",
                    "mensagem": f"Evento '{criado['titulo']}' criado com sucesso!",
                    "dados": criado
                }

            return {
                "status": "confirmacao",
                "acao": "criar",
                "mensagem": "Responda 'sim' para criar o evento ou 'não' para cancelar."
            }

        # 2. Usa a LLM para interpretar o pedido.
        agora = datetime.now(config.FUSO).isoformat(timespec="seconds")
        prompt = PROMPT_SUPERVISOR.format(agora=agora, pedido=pedido)

        try:
            texto_llm = self.consultar_llm(prompt)
            interpretacao = InterpretacaoSupervisor.model_validate(
                extrair_json(texto_llm)
            )
        except (ErroLLM, ValueError, ValidationError, TypeError) as erro:
            return {
                "status": "erro",
                "acao": "interpretar",
                "mensagem": f"Não consegui interpretar o pedido: {erro}"
            }

        # 3. Quando faltam informações.
        if interpretacao.acao == "esclarecer":
            return {
                "status": "esclarecimento",
                "acao": "esclarecer",
                "mensagem": interpretacao.pergunta or "Pode fornecer mais informações?"
            }

        # 4. Quando o estudante quer visualizar a agenda.
        if interpretacao.acao == "visualizar":

            try:
                dados = interpretacao.dados

                if not isinstance(dados, dict) or set(dados) != {"inicio", "fim"}:
                    raise ValueError("Informe início e fim.")

                periodo = PedidoVisualizacao.model_validate(dados)

            except (ValidationError, ValueError, TypeError):
                return {
                    "status": "esclarecimento",
                    "acao": "esclarecer",
                    "mensagem": "Não consegui identificar um período válido."
                }

            try:
                resposta = self.visualizador.executar_json(
                    periodo.model_dump(mode="json")
                )
            except Exception as erro:
                return {
                    "status": "erro",
                    "acao": "visualizar",
                    "mensagem": f"Falha ao consultar a agenda: {erro}"
                }

            if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
                erro = resposta.get("erro") if isinstance(resposta, dict) else None
                mensagem = erro.get("mensagem") if isinstance(erro, dict) else "Falha desconhecida."
                return {
                    "status": "erro",
                    "acao": "visualizar",
                    "mensagem": f"Não foi possível consultar a agenda: {mensagem}"
                }

            try:
                mensagem = _formatar_horarios(resposta)
            except (KeyError, TypeError, ValueError) as erro:
                return {
                    "status": "erro",
                    "acao": "visualizar",
                    "mensagem": f"Resposta inesperada: {erro}"
                }

            return {
                "status": "sucesso",
                "acao": "visualizar",
                "mensagem": mensagem,
                "dados": resposta["dados"]
            }

        # 5. Quando o estudante quer criar um evento.
        if interpretacao.acao == "criar":

            try:
                dados = interpretacao.dados

                if not isinstance(dados, dict) or set(dados) != {"titulo", "inicio", "fim"}:
                    raise ValueError("Informe título, início e fim.")

                evento = PedidoCriacao.model_validate(dados)
                evento = evento.model_dump(mode="json")

            except (ValidationError, ValueError, TypeError):
                return {
                    "status": "esclarecimento",
                    "acao": "esclarecer",
                    "mensagem": "Para criar o evento, informe título, data, horário de início e horário de término."
                }

            if not self.verificar_disponibilidade(evento):
                return {
                    "status": "erro",
                    "acao": "criar",
                    "mensagem": "Não consegui confirmar esse horário como livre. Nenhum evento foi criado."
                }

            self.evento_pendente = evento

            inicio = datetime.fromisoformat(evento["inicio"])
            fim = datetime.fromisoformat(evento["fim"])

            return {
                "status": "confirmacao",
                "acao": "criar",
                "mensagem": (
                    f"Confirma a criação de '{evento['titulo']}' "
                    f"no dia {inicio:%d/%m/%Y}, "
                    f"das {inicio:%H:%M} às {fim:%H:%M}? "
                    "Responda 'sim' ou 'não'."
                )
            }

        # 6. Outras ações ainda não implementadas.
        mensagens = {
            "planejar": "O Planejador ainda não foi integrado ao Supervisor.",
            "fora_escopo": "Posso ajudar a consultar a agenda ou criar eventos."
        }

        return {
            "status": "indisponivel",
            "acao": interpretacao.acao,
            "mensagem": mensagens.get(
                interpretacao.acao,
                "Essa funcionalidade ainda não está disponível."
            )
        }