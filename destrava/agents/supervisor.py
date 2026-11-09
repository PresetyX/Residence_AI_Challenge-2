"""Supervisor do Destrava: visualiza e cria eventos (sem RAG)."""

from datetime import datetime, date, time, timedelta
from typing import Callable, Literal

from pydantic import BaseModel, ValidationError, ConfigDict, Field
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

class TarefaPlanejador(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    etapa: int = Field(ge=0)
    titulo: str = Field(min_length=1)


class RespostaPlanejador(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    tarefas: list[TarefaPlanejador] = Field(min_length=1)

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
        planejador=None,
    ):
        self.visualizador = visualizador if visualizador is not None else AgenteVisualizar()
        self.criador = criador if criador is not None else AgenteCriar()
        self.consultar_llm = consultar_llm if consultar_llm is not None else perguntar

        self.planejador = planejador
        self.evento_pendente = None

        self.cronograma_pendente = None


    
    
    def receber_planejamento(self, projeto: str, prazo: str) -> dict:
        """Recebe e valida as subtarefas devolvidas pelo Planejador."""

        if self.planejador is None:
            return {
                "status": "erro",
                "acao": "planejar",
                "mensagem": "Nenhum Planejador foi conectado."
            }

        if not isinstance(projeto, str) or not projeto.strip():
            return {
                "status": "erro",
                "acao": "planejar",
                "mensagem": "Informe um projeto válido."
            }

        try:
            data_prazo = date.fromisoformat(prazo)

            if data_prazo.isoformat() != prazo:
                raise ValueError()

        except (ValueError, TypeError):
            return {
                "status": "erro",
                "acao": "planejar",
                "mensagem": "Informe o prazo no formato AAAA-MM-DD."
            }

        try:
            resposta = self.planejador.executar(projeto.strip(), prazo)

            plano = RespostaPlanejador.model_validate(resposta)

            tarefas = sorted(
                plano.tarefas,
                key=lambda tarefa: tarefa.etapa
            )

            if any(not tarefa.titulo.strip() for tarefa in tarefas):
                raise ValueError("Existe uma tarefa com título vazio.")

        except (ValidationError, ValueError, TypeError) as erro:
            return {
                "status": "erro",
                "acao": "planejar",
                "mensagem": f"Resposta inválida do Planejador: {erro}"
            }

        except Exception as erro:
            return {
                "status": "erro",
                "acao": "planejar",
                "mensagem": f"Falha ao executar o Planejador: {erro}"
            }

        return {
            "status": "sucesso",
            "acao": "planejar",
            "mensagem": f"Recebi {len(tarefas)} tarefas do Planejador.",
            "dados": {
                "projeto": projeto.strip(),
                "prazo": prazo,
                "tarefas": [tarefa.model_dump() for tarefa in tarefas]
            }
        }

        
    def consultar_periodos_projeto(self, projeto: str, prazo: str) -> dict:
        """Recebe as tarefas e consulta os horários livres até o prazo."""

        # 1. Recebe e valida as tarefas do Planejador.
        planejamento = self.receber_planejamento(projeto, prazo)

        if planejamento["status"] != "sucesso":
            return planejamento

        # 2. Define o período da consulta.
        inicio = datetime.now(config.FUSO)

        data_prazo = date.fromisoformat(prazo)

        # Inclui todo o dia do prazo.
        fim = datetime.combine(
            data_prazo + timedelta(days=1),
            time.min,
            tzinfo=config.FUSO
        )

        if fim <= inicio:
            return {
                "status": "erro",
                "acao": "planejar",
                "mensagem": "O prazo do projeto já passou."
            }

        # 3. Monta o JSON esperado pelo Agente Visualizar.
        pedido_visualizacao = {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat()
        }

        # 4. Solicita os horários livres.
        try:
            resposta = self.visualizador.executar_json(
                pedido_visualizacao
            )

        except Exception as erro:
            return {
                "status": "erro",
                "acao": "visualizar",
                "mensagem": f"Falha ao consultar a agenda: {erro}"
            }

        if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
            return {
                "status": "erro",
                "acao": "visualizar",
                "mensagem": "Não foi possível consultar os horários livres.",
                "erro": resposta.get("erro") if isinstance(resposta, dict) else None
            }

        dados = resposta.get("dados")

        if not isinstance(dados, dict) or not isinstance(dados.get("livres"), list):
            return {
                "status": "erro",
                "acao": "visualizar",
                "mensagem": "O Visualizar retornou dados inválidos."
            }

        # 5. Junta as tarefas e os períodos livres.
        return {
            "status": "sucesso",
            "acao": "planejar",
            "mensagem": "Tarefas e horários livres recebidos com sucesso.",
            "periodo": resposta.get("periodo"),
            "dados": {
                "projeto": projeto.strip(),
                "prazo": prazo,
                "tarefas": planejamento["dados"]["tarefas"],
                "livres": dados["livres"],
                "total_minutos_livres": dados["total_minutos_livres"]
            }
        }
    def preparar_agendamento(self, projeto: str, prazo: str) -> dict:
        """Monta uma prévia: cada tarefa recebe 60 minutos em um horário livre."""
        # Preparar um novo cronograma cancela a prévia anterior.
        self.cronograma_pendente = None

        if self.evento_pendente is not None:
            return {
                "status": "erro", "acao": "planejar",
                "mensagem": "Confirme ou cancele o evento individual pendente primeiro."
            }

        # Aproveita a Etapa 2: tarefas do mock + agenda real do Visualizar.
        consulta = self.consultar_periodos_projeto(projeto, prazo)
        if consulta.get("status") != "sucesso":
            return consulta

        try:
            tarefas = consulta["dados"]["tarefas"]
            livres = consulta["dados"]["livres"]

            # Cada bloco tem início e fim; podemos avançar o início conforme usamos horas.
            blocos = sorted(
                [
                    [datetime.fromisoformat(b["inicio"]), datetime.fromisoformat(b["fim"])]
                    for b in livres
                ],
                key=lambda bloco: bloco[0]
            )

            if not tarefas:
                raise ValueError("Nenhuma tarefa recebida.")

            eventos = []
            for tarefa in tarefas:
                for bloco in blocos:
                    inicio = max(bloco[0], datetime.now(config.FUSO))
                    # Não cria eventos com segundos quebrados, como 15:14:25.
                    if inicio.second or inicio.microsecond:
                        inicio = inicio.replace(second=0, microsecond=0) + timedelta(minutes=1)

                    fim = inicio + timedelta(minutes=60)  # Temporário: rede neural virá depois.
                    if fim <= bloco[1]:
                        eventos.append({
                            "titulo": f"[Destrava] {tarefa['titulo']}",
                            "inicio": inicio.isoformat(),
                            "fim": fim.isoformat(),
                        })
                        bloco[0] = fim  # Reserva esse horário na prévia.
                        break
                else:
                    return {
                        "status": "erro", "acao": "planejar",
                        "mensagem": f"Não há horário livre suficiente para '{tarefa['titulo']}'. Nenhum evento foi criado."
                    }
        except (KeyError, TypeError, ValueError) as erro:
            return {"status": "erro", "acao": "planejar", "mensagem": f"Dados inválidos: {erro}"}

        self.cronograma_pendente = eventos
        return {
            "status": "confirmacao",
            "acao": "planejar",
            "mensagem": "Confira a prévia. Responda 'sim' para criar ou 'não' para cancelar.",
            "dados": {"projeto": projeto, "prazo": prazo, "eventos": eventos}
        }

    def confirmar_agendamento(self, confirmado: bool) -> dict:
        """Cria o cronograma somente com confirmação explícita."""
        eventos = self.cronograma_pendente
        if eventos is None:
            return {"status": "erro", "acao": "planejar", "mensagem": "Não existe cronograma aguardando confirmação."}

        # Apaga a pendência: outro 'sim' não pode repetir a criação.
        self.cronograma_pendente = None

        if not confirmado:
            return {"status": "cancelado", "acao": "planejar", "mensagem": "Cancelado. Nenhum evento foi criado."}

        # Checa TODOS os horários antes de criar o primeiro evento.
        for evento in eventos:
            if not self.verificar_disponibilidade(evento):
                return {
                    "status": "erro", "acao": "planejar",
                    "mensagem": f"O horário de '{evento['titulo']}' não está mais livre. Nenhum evento foi criado."
                }

        criados = []
        for evento in eventos:
            # Também verifica imediatamente antes de cada criação.
            if not self.verificar_disponibilidade(evento):
                return {
                    "status": "parcial" if criados else "erro",
                    "acao": "planejar",
                    "mensagem": "A disponibilidade mudou durante o agendamento. Confira a agenda antes de tentar novamente.",
                    "dados": {"eventos_criados": criados}
                }

            try:
                resposta = self.criador.executar_json(evento)
            except Exception as erro:
                return {
                    "status": "parcial" if criados else "erro",
                    "acao": "planejar",
                    "mensagem": f"Falha ao criar evento: {erro}. Confira a agenda antes de tentar novamente.",
                    "dados": {"eventos_criados": criados}
                }

            if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
                return {
                    "status": "parcial" if criados else "erro",
                    "acao": "planejar",
                    "mensagem": "O Google não confirmou uma das criações. Confira a agenda antes de tentar novamente.",
                    "dados": {"eventos_criados": criados}
                }

            try:
                criado = resposta["dados"]["evento"]
                criados.append(criado)
            except (KeyError, TypeError):
                return {
                    "status": "parcial",
                    "acao": "planejar",
                    "mensagem": "O Criar confirmou sucesso, mas não devolveu os dados do evento. Verifique sua agenda.",
                    "dados": {"eventos_criados": criados}
                }

            # O Criar sinaliza se o Google devolveu um horário diferente do pedido.
            conferencia = (resposta.get("fluxo") or {}).get("fim", {}).get("detalhe") or {}
            if conferencia.get("periodo_confere") is False:
                return {
                    "status": "parcial", "acao": "planejar",
                    "mensagem": "O Google devolveu um horário diferente do solicitado. Verifique sua agenda.",
                    "dados": {"eventos_criados": criados}
                }

        return {
            "status": "sucesso", "acao": "planejar",
            "mensagem": f"{len(criados)} tarefas criadas no Google Calendar!",
            "dados": {"eventos_criados": criados}
        }

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
                self.cronograma_pendente = None

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