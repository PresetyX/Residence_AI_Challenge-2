"""Supervisor do Destrava: interpreta, valida, coordena e solicita confirmação.
"""

from datetime import date, datetime, time, timedelta
from typing import Callable, Literal
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from destrava.tools.criar import AgenteCriar
from destrava.tools.editar import AgenteEditar, PedidoEdicao
from destrava.tools.excluir import AgenteExcluir
from destrava.agents.planejador import PedidoNaoEntendido
from destrava.tools.visualizar import AgenteVisualizar
from destrava.core import config
from destrava.core.llm_client import ErroLLM, extrair_json, perguntar
from destrava.core.models import PedidoCriacao, PedidoVisualizacao
from destrava.core.prazo import interpretar_prazo
from destrava.core.encaixe_pomodoro import encaixar_tarefas_pomodoro, SemEspacoPomodoro, calcular_deficit_minimo, periodo_acordado
from destrava.prompts.supervisor import PROMPT_SUPERVISOR


class InterpretacaoSupervisor(BaseModel):
    acao: Literal["visualizar", "criar", "editar", "excluir", "planejar", "esclarecer", "fora_escopo"]
    dados: dict | None = None
    pergunta: str | None = None


class TarefaPlanejador(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    etapa: int = Field(ge=0)
    titulo: str = Field(min_length=1)
    # Campos que o Planejador também devolve (POST /projetos). São opcionais:
    # o encaixe na agenda usa só etapa e título.
    objetivo: str | None = None
    entregaveis: str | None = None
    demonstracao: str | None = None
    dependencia: int | None = None
    story_points: int | None = None
    # Devolvido pelo POST /projetos (story_points x 60); o encaixe recalcula.
    tempo_estimado_minutos: int | float | None = None


class RespostaPlanejador(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    tarefas: list[TarefaPlanejador] = Field(min_length=1)


def _formatar_horarios(resposta: dict) -> str:
    dados = resposta["dados"]
    livres = dados["livres"]
    if not livres:
        return "Não encontrei horários livres no período consultado."

    minutos = round(float(dados["total_minutos_livres"]))
    horas, resto = divmod(minutos, 60)
    linhas = [f"Você tem {horas}h{resto:02d}min livres no período consultado:"]
    for bloco in livres:
        inicio = datetime.fromisoformat(bloco["inicio"])
        fim = datetime.fromisoformat(bloco["fim"])
        if inicio.date() == fim.date():
            linhas.append(f"- {inicio:%d/%m}, das {inicio:%H:%M} às {fim:%H:%M}")
        else:
            linhas.append(f"- {inicio:%d/%m %H:%M} até {fim:%d/%m %H:%M}")
    return "\n".join(linhas)


def _formatar_eventos(resposta: dict) -> tuple[str, list[dict]]:
    dados = resposta.get("dados")
    ocupados = dados.get("ocupados") if isinstance(dados, dict) else None
    if not isinstance(ocupados, list):
        raise ValueError("O Visualizar não retornou uma lista válida de eventos.")

    eventos = [
        evento for evento in ocupados
        if isinstance(evento, dict) and evento.get("tipo") in ("evento", "dia_inteiro")
    ]
    if not eventos:
        return "Não encontrei eventos marcados no período consultado.", []

    linhas = ["Seus eventos marcados no período:"]
    for evento in eventos:
        inicio = datetime.fromisoformat(evento["inicio"])
        fim = datetime.fromisoformat(evento["fim"])
        titulo = evento.get("titulo") or "Evento sem título"
        if evento.get("tipo") == "dia_inteiro":
            horario = "dia inteiro"
        elif inicio.date() == fim.date():
            horario = f"das {inicio:%H:%M} às {fim:%H:%M}"
        else:
            horario = f"{inicio:%d/%m %H:%M} até {fim:%d/%m %H:%M}"
        linhas.append(f"- {titulo}: {inicio:%d/%m/%Y}, {horario}")
    return "\n".join(linhas), eventos


def _normalizar(texto: str) -> str:
    """Apenas para identificar datas/horários escritos pelo estudante."""
    letras = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in letras if unicodedata.category(c) != "Mn")


def _data_do_pedido(texto: str, agora: datetime) -> tuple[date | None, str | None]:
    """Valida datas explícitas antes que a LLM possa alterá-las."""
    texto = _normalizar(texto)
    datas: list[date] = []
    formatos = (
        (r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)", "BR"),
        (r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", "ISO"),
    )
    for padrao, formato in formatos:
        for achado in re.finditer(padrao, texto):
            partes = [int(p) for p in achado.groups()]
            dia, mes, ano = partes if formato == "BR" else partes[::-1]
            try:
                datas.append(date(ano, mes, dia))
            except ValueError:
                return None, f"A data {achado.group()} não existe. Informe uma data válida."

    if re.search(r"\bdepois de amanha\b", texto):
        datas.append(agora.date() + timedelta(days=2))
        texto = re.sub(r"\bdepois de amanha\b", "", texto)
    if re.search(r"\bamanha\b", texto):
        datas.append(agora.date() + timedelta(days=1))
    if re.search(r"\bhoje\b", texto):
        datas.append(agora.date())

    if len(set(datas)) > 1:
        return None, "Foram informadas datas diferentes. Envie um novo pedido completo."
    return (datas[0] if datas else None), None


def _horarios_do_pedido(texto: str) -> tuple[tuple[time, time] | None, str | None]:
    """Aceita 'das 13h às 14h', 'das 13 às 14' e 'das 1 às 3 da manhã'.

    Expressões não reconhecidas são rejeitadas, nunca preenchidas pela IA.
    """
    texto = _normalizar(texto)
    padrao = (
        r"\b(?:das|de)\s+(\d{1,2})(?:(?:h|:)(\d{0,2}))?"
        r"\s+(?:as|a|ate)\s+(\d{1,2})(?:(?:h|:)(\d{0,2}))?"
        r"(?=\s|$|[.,;!?])"
    )
    encontrados = []
    for achado in re.finditer(padrao, texto):
        h1, m1, h2, m2 = achado.groups()
        horas = [int(h1), int(h2)]
        minutos = [int(m1 or 0), int(m2 or 0)]
        restante = texto[achado.end():]
        qualificador = re.match(r"\s+(?:da|de|do)\s+(manha|tarde|noite|madrugada)\b", restante)
        periodo = qualificador.group(1) if qualificador else None

        if any(h > 23 for h in horas) or any(m > 59 for m in minutos):
            return None, "Há horários inválidos. Use horas de 00 a 23 e minutos de 00 a 59."
        if not periodo and max(horas) <= 12 and not any(x in achado.group() for x in ("h", ":")):
            return None, "Informe se é manhã/tarde/noite ou use formato 24h (ex.: das 13h às 14h)."
        if periodo in ("tarde", "noite"):
            if periodo == "noite" and any(h <= 5 for h in horas):
                return None, "O horário da noite ficou ambíguo. Informe em formato 24h."
            horas = [h + 12 if 1 <= h <= 11 else h for h in horas]
        elif periodo in ("manha", "madrugada") and (any(h > 12 for h in horas) or (periodo == "manha" and 12 in horas)):
            return None, "O período informado não combina com o horário. Use formato 24h."
        encontrados.append((time(horas[0], minutos[0]), time(horas[1], minutos[1])))

    if len(set(encontrados)) > 1:
        return None, "Você informou intervalos diferentes. Envie um novo pedido completo."
    return (encontrados[0] if encontrados else None), None


def _conferir_texto(pedido: str, inicio: datetime, fim: datetime, agora: datetime) -> str | None:
    """Confere se a LLM preservou a data e os horários explícitos do pedido."""
    data, erro = _data_do_pedido(pedido, agora)
    if erro:
        return erro
    if data is None:
        return "Informe a data do evento (ex.: amanhã ou 12/11/2026) em um novo pedido completo."
    intervalo, erro = _horarios_do_pedido(pedido)
    if erro:
        return erro
    if intervalo is None:
        return "Informe os horários de início e fim em um novo pedido completo (ex.: das 13h às 14h)."

    inicio = inicio.replace(tzinfo=config.FUSO) if inicio.tzinfo is None else inicio.astimezone(config.FUSO)
    fim = fim.replace(tzinfo=config.FUSO) if fim.tzinfo is None else fim.astimezone(config.FUSO)
    if inicio.date() != data or fim.date() != data:
        return "A IA alterou a data solicitada. Nenhum evento foi criado. Envie novamente o pedido completo."
    if (inicio.time().replace(tzinfo=None), fim.time().replace(tzinfo=None)) != intervalo:
        h1, h2 = intervalo
        return (f"A IA interpretou {inicio:%H:%M} às {fim:%H:%M}, "
                f"mas você informou {h1:%H:%M} às {h2:%H:%M}. "
                "Nenhum evento foi criado. Envie um novo pedido completo.")
    return None


def _horario_acordado(inicio: datetime, fim: datetime) -> bool:
    """Proteção adicional ao cálculo de sono existente no agenda_engine.py."""
    inicio = inicio.astimezone(config.FUSO)
    fim = fim.astimezone(config.FUSO)
    # O evento cabe inteiro num período acordado (do perfil do usuário). Quem
    # dorme depois da meia-noite ainda está no período do dia anterior.
    for dia in (inicio.date() - timedelta(days=1), inicio.date()):
        acordar, dormir = periodo_acordado(dia)
        if acordar <= inicio and fim <= dormir:
            return True
    return False


class AgenteSupervisor:
    def __init__(
        self,
        visualizador: AgenteVisualizar | None = None,
        criador: AgenteCriar | None = None,
        consultar_llm: Callable[[str], str] | None = None,
        planejador=None,
        editor: AgenteEditar | None = None,
        excluidor: AgenteExcluir | None = None,
    ):
        self.visualizador = visualizador if visualizador is not None else AgenteVisualizar()
        self.criador = criador if criador is not None else AgenteCriar()
        self.editor = editor if editor is not None else AgenteEditar()
        self.excluidor = excluidor if excluidor is not None else AgenteExcluir()
        self.consultar_llm = consultar_llm if consultar_llm is not None else perguntar
        self.planejador = planejador
        # Apenas estados de confirmação; não guardamos pedidos incompletos.
        self.evento_pendente = None
        self.cronograma_pendente = None
        self.operacao_pendente = None

    def interpretar_prazo(self, texto: str) -> date | None:
        """Prazo de entrega escrito no pedido ("até amanhã", "tenho uma semana", "20/12")."""
        return interpretar_prazo(texto, datetime.now(config.FUSO))

    def receber_planejamento(self, projeto: str, prazo: str, tarefas: list | None = None) -> dict:
        """Recebe e valida as subtarefas devolvidas pelo Planejador.

        Com ``tarefas`` (um plano já gerado, ex.: o do POST /projetos), valida
        essas tarefas em vez de chamar o Planejador de novo.
        """

        if self.planejador is None and tarefas is None:
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
            resposta = (
                {"tarefas": tarefas}
                if tarefas is not None
                else self.planejador.executar(projeto.strip(), prazo)
            )

            plano = RespostaPlanejador.model_validate(resposta)

            tarefas = sorted(
                plano.tarefas,
                key=lambda tarefa: tarefa.etapa
            )

            if any(not tarefa.titulo.strip() for tarefa in tarefas):
                raise ValueError("Existe uma tarefa com título vazio.")

        except PedidoNaoEntendido as erro:
            # O Planejador não entendeu o projeto: pede mais detalhes ao usuário.
            return {
                "status": "esclarecimento",
                "acao": "planejar",
                "mensagem": str(erro)
            }

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
                "tarefas": [tarefa.model_dump(exclude_none=True) for tarefa in tarefas]
            }
        }

        
    def consultar_periodos_projeto(self, projeto: str, prazo: str, tarefas: list | None = None) -> dict:
        """Recebe as tarefas e consulta os horários livres até o prazo."""

        # 1. Recebe e valida as tarefas do Planejador.
        planejamento = self.receber_planejamento(projeto, prazo, tarefas)

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
    def preparar_agendamento(self, projeto: str, prazo: str, tarefas: list | None = None) -> dict:
        """Classifica o prazo e prepara a previa, sem criar eventos."""
        self.cronograma_pendente = None
        if self.evento_pendente is not None:
            return {
                "status": "erro", "acao": "planejar",
                "mensagem": "Confirme ou cancele o evento individual pendente primeiro."
            }
        if self.operacao_pendente is not None:
            return {
                "status": "erro", "acao": "planejar",
                "mensagem": "Confirme ou cancele a alteração de evento pendente primeiro."
            }

        consulta = self.consultar_periodos_projeto(projeto, prazo, tarefas)
        if consulta.get("status") != "sucesso":
            return consulta

        tarefas = consulta["dados"]["tarefas"]
        livres = consulta["dados"]["livres"]
        agora = datetime.now(config.FUSO)

        try:
            try:
                eventos, detalhes = encaixar_tarefas_pomodoro(
                    tarefas, livres, agora=agora,
                )
                classificacao = "tranquilo"
            except SemEspacoPomodoro:
                # Recalcula TODAS as tarefas sem Pomodoro, nao apenas as que faltaram.
                try:
                    eventos, detalhes = encaixar_tarefas_pomodoro(
                        tarefas, livres, agora=agora, usar_pomodoro=False,
                    )
                    classificacao = "corrido"
                except SemEspacoPomodoro:
                    deficit = calcular_deficit_minimo(
                        tarefas, livres, agora=agora,
                    )
                    if deficit:
                        motivo = (f"Faltam pelo menos {deficit} minutos de "
                                  "capacidade, mantendo 2h livres por dia.")
                    else:
                        motivo = ("A soma dos minutos seria suficiente, mas "
                                  "as janelas livres nao comportam todas as tarefas.")
                    return {
                        "status": "erro", "acao": "planejar",
                        "classificacao": "impossivel",
                        "mensagem": ("Prazo IMPOSSIVEL: as tarefas nao cabem "
                                     "ate a data limite, nem sem Pomodoro. " + motivo +
                                     " Nenhum evento foi criado."),
                        "dados": {
                            "projeto": projeto, "prazo": prazo,
                            "classificacao": "impossivel",
                            "minutos_faltantes_minimos": deficit,
                            "eventos": [],
                        },
                    }
        except (ValueError, KeyError, TypeError) as erro:
            return {"status": "erro", "acao": "planejar", "mensagem": str(erro)}

        self.cronograma_pendente = eventos
        if classificacao == "tranquilo":
            mensagem = ("Prazo TRANQUILO: todas as tarefas cabem com Pomodoro "
                        "e com a reserva diaria de 2h. Confira a previa e "
                        "responda 'sim' ou 'nao'.")
        else:
            mensagem = ("Prazo CORRIDO: com Pomodoro nao coube. "
                        "Todas as tarefas foram reorganizadas SEM Pomodoro, "
                        "mantendo 2h livres por dia. Confira a previa e "
                        "responda 'sim' ou 'nao'.")
        return {
            "status": "confirmacao", "acao": "planejar",
            "classificacao": classificacao,
            "mensagem": mensagem,
            "dados": {
                "projeto": projeto, "prazo": prazo,
                "classificacao": classificacao,
                "eventos": eventos,
                "pomodoros": detalhes,
            },
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
        """Só permite horários acordado que estejam inteiramente livres na agenda."""
        try:
            inicio = datetime.fromisoformat(evento["inicio"])
            fim = datetime.fromisoformat(evento["fim"])
            if inicio >= fim or not _horario_acordado(inicio, fim):
                return False
            # O Visualizar filtra janelas menores que DURACAO_MINIMA_LIVRE.
            # Para uma parte curta, confira os ocupados do intervalo exato,
            # sem alterar a configuração de visualização nem forçar um gap.
            if fim - inicio < config.DURACAO_MINIMA_LIVRE:
                resposta = self.visualizador.executar_json(
                    {"inicio": evento["inicio"], "fim": evento["fim"]},
                    incluir_ocupados=True,
                )
                if resposta.get("status") != "sucesso":
                    return False
                ocupados = resposta["dados"]["ocupados"]
                if not isinstance(ocupados, list):
                    return False
                for bloco in ocupados:
                    if bloco["tipo"] == "dia_inteiro" and not config.DIA_INTEIRO_BLOQUEIA:
                        continue
                    a = datetime.fromisoformat(bloco["inicio"])
                    b = datetime.fromisoformat(bloco["fim"])
                    if a < fim and b > inicio:
                        return False
                return True
            resposta = self.visualizador.executar_json({
                "inicio": evento["inicio"], "fim": evento["fim"]
            })
            if resposta.get("status") != "sucesso":
                return False
            for bloco in resposta["dados"]["livres"]:
                livre_inicio = datetime.fromisoformat(bloco["inicio"])
                livre_fim = datetime.fromisoformat(bloco["fim"])
                if livre_inicio <= inicio and livre_fim >= fim:
                    return True
        except Exception:
            # Não permita agendar sem uma consulta de disponibilidade válida.
            return False
        return False

    def _localizar_evento(self, dados: dict) -> tuple[dict | None, dict | None]:
        """Localiza um evento pelo título e dia antes de propor uma alteração."""
        titulo = dados.get("titulo_evento")
        dia_texto = dados.get("data_evento")
        if not isinstance(titulo, str) or not titulo.strip():
            return None, {"status": "esclarecimento", "acao": "esclarecer",
                          "mensagem": "Informe o título do evento que deseja alterar ou excluir."}
        try:
            dia = date.fromisoformat(dia_texto)
            if dia.isoformat() != dia_texto:
                raise ValueError()
        except (ValueError, TypeError):
            return None, {"status": "esclarecimento", "acao": "esclarecer",
                          "mensagem": "Informe a data do evento que deseja alterar ou excluir."}

        try:
            resposta = self.visualizador.executar_json(
                {
                    "inicio": datetime.combine(dia, time.min, tzinfo=config.FUSO).isoformat(),
                    "fim": datetime.combine(dia + timedelta(days=1), time.min, tzinfo=config.FUSO).isoformat(),
                },
                incluir_ocupados=True,
            )
        except Exception as erro:
            return None, {"status": "erro", "acao": "visualizar",
                          "mensagem": f"Falha ao localizar o evento na agenda: {erro}"}

        if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
            detalhe = resposta.get("erro") if isinstance(resposta, dict) else None
            mensagem = detalhe.get("mensagem") if isinstance(detalhe, dict) else "Falha desconhecida."
            return None, {"status": "erro", "acao": "visualizar",
                          "mensagem": f"Não foi possível consultar os eventos: {mensagem}"}

        dados_resposta = resposta.get("dados")
        ocupados = dados_resposta.get("ocupados") if isinstance(dados_resposta, dict) else None
        if not isinstance(ocupados, list):
            return None, {"status": "erro", "acao": "visualizar",
                          "mensagem": "A agenda não devolveu uma lista válida de eventos."}

        eventos = [
            evento for evento in ocupados
            if isinstance(evento, dict)
            and evento.get("tipo") in ("evento", "dia_inteiro")
            and str(evento.get("inicio", ""))[:10] == dia.isoformat()
        ]
        titulo_normalizado = _normalizar(titulo.strip())
        candidatos = [
            evento for evento in eventos
            if isinstance(evento.get("titulo"), str)
            and _normalizar(evento["titulo"].strip()) == titulo_normalizado
        ]
        hora = dados.get("hora_evento")
        if hora is not None:
            if not isinstance(hora, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", hora):
                return None, {"status": "esclarecimento", "acao": "esclarecer",
                              "mensagem": "Informe o horário de início do evento no formato HH:MM."}
            candidatos = [
                evento for evento in candidatos
                if str(evento.get("inicio", ""))[11:16] == hora
            ]

        if len(candidatos) == 1:
            evento = candidatos[0]
            return {
                "id": evento.get("id"),
                "titulo": evento.get("titulo"),
                "inicio": evento.get("inicio"),
                "fim": evento.get("fim"),
            }, None

        if candidatos:
            opcoes = ", ".join(
                f"{evento.get('titulo')} às {str(evento.get('inicio', ''))[11:16]}"
                for evento in candidatos
            )
            mensagem = f"Encontrei mais de um evento com esse título nessa data ({opcoes}). Informe o horário de início."
        else:
            disponiveis = ", ".join(
                f"{evento.get('titulo')} às {str(evento.get('inicio', ''))[11:16]}"
                for evento in eventos
            )
            complemento = f" Eventos nessa data: {disponiveis}." if disponiveis else " Não há eventos nessa data."
            mensagem = f"Não encontrei '{titulo.strip()}' nessa data.{complemento} Confira o título e a data."
        return None, {"status": "esclarecimento", "acao": "esclarecer", "mensagem": mensagem}

    def _preparar_operacao_evento(self, acao: str, dados: dict | None) -> dict:
        """Resolve o alvo e deixa edição/exclusão aguardando confirmação."""
        dados_esperados = {"titulo_evento", "data_evento"}
        dados_opcionais = {"hora_evento"}
        if acao == "editar":
            dados_esperados.add("alteracoes")
        if acao == "editar" and isinstance(dados, dict):
            if not dados_esperados.issubset(dados) or set(dados) - dados_esperados - dados_opcionais:
                return {"status": "esclarecimento", "acao": "esclarecer",
                        "mensagem": "Informe o título e a data do evento, além dos campos que deseja alterar."}
            alteracoes = dados.get("alteracoes")
            campos_validos = {"titulo", "inicio", "fim", "descricao", "local"}
            if not isinstance(alteracoes, dict) or not alteracoes or set(alteracoes) - campos_validos:
                return {"status": "esclarecimento", "acao": "esclarecer",
                        "mensagem": "Diga quais informações do evento deseja alterar."}
            try:
                pedido_edicao = PedidoEdicao.model_validate({"id": "alvo", **alteracoes})
                alteracoes = pedido_edicao.model_dump(mode="json", exclude={"id"}, exclude_none=True)
            except ValidationError as erro:
                detalhe = erro.errors(include_url=False, include_context=False)[0].get("msg", "Dados inválidos.")
                return {"status": "esclarecimento", "acao": "esclarecer",
                        "mensagem": detalhe.removeprefix("Value error, ")}
            if not alteracoes:
                return {"status": "esclarecimento", "acao": "esclarecer",
                        "mensagem": "Diga quais informações do evento deseja alterar."}
        elif acao == "excluir" and isinstance(dados, dict):
            if not dados_esperados.issubset(dados) or set(dados) - dados_esperados - dados_opcionais:
                return {"status": "esclarecimento", "acao": "esclarecer",
                        "mensagem": "Informe o título e a data do evento que deseja excluir."}
            alteracoes = None
        else:
            return {"status": "esclarecimento", "acao": "esclarecer",
                    "mensagem": "Informe os dados do evento e as alterações desejadas."}

        evento, erro = self._localizar_evento(dados)
        if erro:
            return erro
        if not evento or not isinstance(evento.get("id"), str) or not evento["id"]:
            return {"status": "erro", "acao": acao,
                    "mensagem": "O evento localizado não tem um ID válido. Nenhuma alteração foi feita."}

        entrada = {"id": evento["id"], **(alteracoes or {})}
        self.operacao_pendente = {"acao": acao, "entrada": entrada, "evento": evento}
        inicio = datetime.fromisoformat(evento["inicio"])
        fim = datetime.fromisoformat(evento["fim"])
        quando = f"{inicio:%d/%m/%Y}, às {inicio:%H:%M}"
        if fim.date() == inicio.date():
            quando += f"-{fim:%H:%M}"
        if acao == "excluir":
            mensagem = f"Confirma a exclusão de '{evento['titulo']}' em {quando}? Responda 'sim' ou 'não'."
        else:
            descricao = []
            rotulos = {"titulo": "título", "inicio": "início", "fim": "fim", "descricao": "descrição", "local": "local"}
            for campo, valor in alteracoes.items():
                exibido = valor
                if campo in ("inicio", "fim"):
                    momento = datetime.fromisoformat(valor)
                    exibido = momento.strftime("%d/%m/%Y às %H:%M")
                descricao.append(f"{rotulos[campo]}: {exibido or '(vazio)'}")
            mensagem = (
                f"Confirma a edição de '{evento['titulo']}' em {quando}? "
                f"Alterações: {'; '.join(descricao)}. Responda 'sim' ou 'não'."
            )
        return {"status": "confirmacao", "acao": acao, "mensagem": mensagem}

    def _confirmar_operacao_evento(self, confirmado: bool) -> dict:
        operacao = self.operacao_pendente
        self.operacao_pendente = None
        if not confirmado:
            return {"status": "cancelado", "acao": operacao["acao"],
                    "mensagem": "Operação cancelada. Nenhuma alteração foi feita."}

        acao = operacao["acao"]
        agente = self.editor if acao == "editar" else self.excluidor
        try:
            resposta = agente.executar_json(operacao["entrada"])
        except Exception as erro:
            return {"status": "erro", "acao": acao, "mensagem": f"Falha ao {acao} o evento: {erro}"}
        if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
            detalhe = resposta.get("erro") if isinstance(resposta, dict) else None
            mensagem = detalhe.get("mensagem") if isinstance(detalhe, dict) else "Falha desconhecida."
            return {"status": "erro", "acao": acao, "mensagem": f"Não foi possível {acao} o evento: {mensagem}"}

        if acao == "editar":
            evento = (resposta.get("dados") or {}).get("evento")
            if not isinstance(evento, dict):
                return {"status": "erro", "acao": acao,
                        "mensagem": "A edição foi confirmada, mas os dados do evento não foram devolvidos. Confira sua agenda."}
            return {"status": "sucesso", "acao": acao,
                    "mensagem": f"Evento '{evento.get('titulo', 'sem título')}' atualizado com sucesso!",
                    "dados": {"evento": evento}}

        evento = operacao["evento"]
        return {"status": "sucesso", "acao": acao,
                "mensagem": f"Evento '{evento['titulo']}' excluído com sucesso.",
                "dados": {"evento_id": evento["id"], "titulo": evento["titulo"], "evento": evento}}

    def executar(self, pedido: str) -> dict:
        """Interpreta cada pedido de forma independente, sem memória de esclarecimentos."""
        if not isinstance(pedido, str) or not pedido.strip():
            return {"status": "erro", "acao": "esclarecer", "mensagem": "Descreva o que deseja fazer."}
        pedido = pedido.strip()

        if self.operacao_pendente is not None:
            resposta = _normalizar(pedido)
            if resposta in ("nao", "cancelar"):
                return self._confirmar_operacao_evento(False)
            if resposta == "sim":
                return self._confirmar_operacao_evento(True)
            return {"status": "confirmacao", "acao": self.operacao_pendente["acao"],
                    "mensagem": "Responda 'sim' para confirmar ou 'não' para cancelar a operação."}

        # A única mensagem contextual é 'sim'/'não' para um evento já confirmado na prévia.
        if self.evento_pendente is not None:
            if _normalizar(pedido) in ("nao", "cancelar"):
                self.evento_pendente = None
                return {"status": "cancelado", "acao": "criar", "mensagem": "Criação cancelada. Nenhum evento foi criado."}
            if _normalizar(pedido) == "sim":
                evento = self.evento_pendente
                self.evento_pendente = None
                self.cronograma_pendente = None
                try:
                    # O início pode ter passado desde que a prévia foi mostrada.
                    PedidoCriacao.model_validate(evento)
                except ValidationError:
                    return {"status": "erro", "acao": "criar", "mensagem": "O evento já não está em uma data futura. Nenhum evento foi criado."}
                if not self.verificar_disponibilidade(evento):
                    return {"status": "erro", "acao": "criar", "mensagem": "Esse horário não está mais disponível. Nenhum evento foi criado."}
                try:
                    resposta = self.criador.executar_json(evento)
                except Exception as erro:
                    return {"status": "erro", "acao": "criar", "mensagem": f"Falha ao criar evento: {erro}"}
                if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
                    detalhe = resposta.get("erro") if isinstance(resposta, dict) else None
                    mensagem = detalhe.get("mensagem") if isinstance(detalhe, dict) else "Falha desconhecida."
                    return {"status": "erro", "acao": "criar", "mensagem": f"Não foi possível criar o evento: {mensagem}"}
                try:
                    criado = resposta["dados"]["evento"]
                    return {"status": "sucesso", "acao": "criar", "mensagem": f"Evento '{criado['titulo']}' criado com sucesso!", "dados": criado}
                except (KeyError, TypeError):
                    return {"status": "erro", "acao": "criar", "mensagem": "O Google confirmou a criação, mas não devolveu os dados. Confira sua agenda antes de tentar novamente."}
            return {"status": "confirmacao", "acao": "criar", "mensagem": "Responda 'sim' para criar o evento ou 'não' para cancelar."}

        agora_dt = datetime.now(config.FUSO)
        # A verificação de data inexistente acontece ANTES da Gemma.
        _, erro_data = _data_do_pedido(pedido, agora_dt)
        if erro_data:
            return {"status": "esclarecimento", "acao": "esclarecer", "mensagem": erro_data}

        # Para criação explicitamente solicitada, exige tudo na mesma mensagem.
        texto_normalizado = _normalizar(pedido)
        quer_criar = re.search(r"\b(crie|criar|cria|agende|agendar|marque|marcar)\b", texto_normalizado)
        if quer_criar:
            data, _ = _data_do_pedido(pedido, agora_dt)
            intervalo, erro_horario = _horarios_do_pedido(pedido)
            if erro_horario:
                return {"status": "esclarecimento", "acao": "esclarecer", "mensagem": erro_horario}
            if data is None or intervalo is None:
                return {"status": "esclarecimento", "acao": "esclarecer",
                        "mensagem": "Para criar um evento, informe título, data e horários de início e término na mesma mensagem. Ex.: Crie uma reunião amanhã das 13h às 14h."}

        try:
            prompt = PROMPT_SUPERVISOR.format(
                agora=agora_dt.isoformat(timespec="seconds"), pedido=pedido
            )
            texto_llm = self.consultar_llm(prompt)
            interpretacao = InterpretacaoSupervisor.model_validate(extrair_json(texto_llm))
        except (ErroLLM, ValueError, ValidationError, TypeError) as erro:
            return {"status": "erro", "acao": "interpretar", "mensagem": f"Não consegui interpretar o pedido: {erro}"}

        if interpretacao.acao == "esclarecer":
            return {"status": "esclarecimento", "acao": "esclarecer",
                    "mensagem": (interpretacao.pergunta or "Informações insuficientes.") + " Envie um novo pedido completo."}

        if interpretacao.acao == "visualizar":
            try:
                dados = interpretacao.dados
                campos_validos = {"inicio", "fim", "tipo"}
                if (
                    not isinstance(dados, dict)
                    or not {"inicio", "fim"}.issubset(dados)
                    or set(dados) - campos_validos
                ):
                    raise ValueError("Informe início e fim.")
                tipo = dados.get("tipo", "livres")
                if tipo not in ("livres", "eventos"):
                    raise ValueError("Escolha entre consultar horários livres ou eventos marcados.")
                periodo = PedidoVisualizacao.model_validate(
                    {"inicio": dados["inicio"], "fim": dados["fim"]}
                )
            except (ValidationError, ValueError, TypeError):
                return {"status": "esclarecimento", "acao": "esclarecer", "mensagem": "Não consegui identificar um período válido para consulta."}
            try:
                entrada = periodo.model_dump(mode="json")
                if tipo == "eventos":
                    resposta = self.visualizador.executar_json(entrada, incluir_ocupados=True)
                else:
                    resposta = self.visualizador.executar_json(entrada)
            except Exception as erro:
                return {"status": "erro", "acao": "visualizar", "mensagem": f"Falha ao consultar a agenda: {erro}"}
            if not isinstance(resposta, dict) or resposta.get("status") != "sucesso":
                detalhe = resposta.get("erro") if isinstance(resposta, dict) else None
                mensagem = detalhe.get("mensagem") if isinstance(detalhe, dict) else "Falha desconhecida."
                return {"status": "erro", "acao": "visualizar", "mensagem": f"Não foi possível consultar a agenda: {mensagem}"}
            try:
                if tipo == "eventos":
                    mensagem, eventos = _formatar_eventos(resposta)
                    return {"status": "sucesso", "acao": "visualizar",
                            "mensagem": mensagem, "dados": {"eventos": eventos}}
                return {"status": "sucesso", "acao": "visualizar",
                        "mensagem": _formatar_horarios(resposta), "dados": resposta["dados"]}
            except (KeyError, TypeError, ValueError) as erro:
                return {"status": "erro", "acao": "visualizar", "mensagem": f"Resposta inesperada: {erro}"}

        if interpretacao.acao == "criar":
            dados = interpretacao.dados
            if not isinstance(dados, dict) or set(dados) != {"titulo", "inicio", "fim"}:
                return {"status": "esclarecimento", "acao": "esclarecer",
                        "mensagem": "Informe título, data, início e término em um novo pedido completo."}
            try:
                inicio_llm = datetime.fromisoformat(dados["inicio"])
                fim_llm = datetime.fromisoformat(dados["fim"])
                erro = _conferir_texto(pedido, inicio_llm, fim_llm, agora_dt)
                if erro:
                    return {"status": "esclarecimento", "acao": "esclarecer", "mensagem": erro}
                evento = PedidoCriacao.model_validate(dados).model_dump(mode="json", exclude_none=True)
            except ValidationError as erro:
                detalhe = erro.errors()[0].get("msg", "Dados inválidos.")
                return {"status": "esclarecimento", "acao": "esclarecer", "mensagem": detalhe.removeprefix("Value error, ")}
            except (ValueError, TypeError, KeyError):
                return {"status": "esclarecimento", "acao": "esclarecer", "mensagem": "Dados inválidos. Envie um novo pedido com título, data e horários."}

            inicio = datetime.fromisoformat(evento["inicio"])
            fim = datetime.fromisoformat(evento["fim"])
            if not _horario_acordado(inicio, fim):
                return {"status": "erro", "acao": "criar",
                        "mensagem": ("Não é possível criar eventos durante o sono "
                                     f"({config.HORARIO_DORMIR:%H:%M} às {config.HORARIO_ACORDAR:%H:%M}). Nenhum evento foi criado.")}
            if not self.verificar_disponibilidade(evento):
                return {"status": "erro", "acao": "criar", "mensagem": "Não consegui confirmar esse horário como livre. Nenhum evento foi criado."}

            self.evento_pendente = evento
            return {"status": "confirmacao", "acao": "criar",
                    "mensagem": (f"Confirma a criação de '{evento['titulo']}' "
                                 f"no dia {inicio:%d/%m/%Y}, das {inicio:%H:%M} às {fim:%H:%M}? "
                                 "Responda 'sim' ou 'não'.")}

        if interpretacao.acao in ("editar", "excluir"):
            return self._preparar_operacao_evento(interpretacao.acao, interpretacao.dados)

        mensagens = {
            "planejar": "O Planejador ainda não foi integrado ao fluxo por texto do Supervisor.",
            "fora_escopo": "Posso ajudar a consultar, criar, editar ou excluir eventos da agenda.",
        }
        return {"status": "indisponivel", "acao": interpretacao.acao,
                "mensagem": mensagens.get(interpretacao.acao, "Essa funcionalidade ainda não está disponível.")}
