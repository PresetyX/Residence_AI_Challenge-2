"""
Agente de visualização da agenda.


Busca os eventos do Google Agenda (somente leitura) e calcula ocupados,
livres e conflitos com o core/agenda_engine.py.


Segue o contrato padrão dos agentes (core/resposta.py):

    inicio -> extrair_periodo(): o LLM transforma o pedido em {"inicio", "fim"}.
    meio   -> executar(): busca os eventos no Google (somente leitura) e
              calcula ocupados, livres e conflitos.
    fim    -> montar_mensagem(): o código resume a agenda em português
              (sem LLM).

Contrato final (usado pelo supervisor):
    AgenteVisualizar().executar_por_texto(pergunta) -> RespostaAgente
    (use .para_dict() ou .para_json() para obter o JSON)
"""


from datetime import date, datetime, time, timedelta


from destrava.core import config
from destrava.core.agenda_engine import montar_visualizacao, normalizar_fuso
from destrava.core.google_client import get_service, listar_eventos
from destrava.core.llm_client import extrair_json, perguntar
from destrava.core.resposta import (
    Periodo,
    RespostaAgente,
    ResultadoExecucao,
    executar_fluxo,
)
from destrava.prompts.visualizar import PROMPT_EXTRACAO



def converter_evento_google(evento: dict) -> dict | None:
    """Converte um evento da API do Google para o formato do ``Bloco``.


    - Evento com horário (``dateTime``): tipo "evento".
    - Evento de dia inteiro (só ``date``): tipo "dia_inteiro", de 00:00 do
      primeiro dia até 00:00 do dia seguinte ao último. O Google já envia o
      fim como o dia seguinte (fim exclusivo), então ele é usado direto.
      Se ele ocupa horário ou não é decidido por config.DIA_INTEIRO_BLOQUEIA.


    Returns:
        Dicionário com id, titulo, inicio, fim e tipo, ou None se o evento
        não tiver início e fim.
    """
    inicio_google = evento.get("start", {})
    fim_google = evento.get("end", {})


    if inicio_google.get("dateTime") and fim_google.get("dateTime"):
        inicio = datetime.fromisoformat(
            inicio_google["dateTime"].replace("Z", "+00:00")
        )
        fim = datetime.fromisoformat(fim_google["dateTime"].replace("Z", "+00:00"))
        tipo = "evento"
    elif inicio_google.get("date") and fim_google.get("date"):
        inicio = datetime.combine(
            date.fromisoformat(inicio_google["date"]), time.min, tzinfo=config.FUSO
        )
        fim = datetime.combine(
            date.fromisoformat(fim_google["date"]), time.min, tzinfo=config.FUSO
        )
        tipo = "dia_inteiro"
    else:
        return None


    return {
        "id": evento.get("id", ""),
        "titulo": evento.get("summary", "Compromisso"),
        "inicio": inicio,
        "fim": fim,
        "tipo": tipo,
    }



def extrair_periodo_detalhado(pergunta: str) -> dict:
    """Usa o LLM para transformar o pedido em um período de datas.

    Args:
        pergunta: pedido do usuário em texto livre.

    Returns:
        Dicionário com ``inicio`` e ``fim`` (datetime no fuso do projeto) e
        ``periodo_padrao`` (True se o modelo falhou e foi usado o fallback).

    Se o modelo não devolver um JSON válido (ou devolver um período
    inválido), usa os próximos 7 dias como fallback seguro.
    """
    hoje = datetime.now(config.FUSO)
    hoje_iso = hoje.date().isoformat()

    prompt = PROMPT_EXTRACAO.format(
        data_de_hoje=hoje_iso,
        fuso=str(config.FUSO),
        pergunta_do_usuario=pergunta,
    )

    resposta = perguntar(prompt)

    try:
        dados = extrair_json(resposta)
        inicio = normalizar_fuso(datetime.fromisoformat(dados["inicio"]))
        fim = normalizar_fuso(datetime.fromisoformat(dados["fim"]))
        if fim <= inicio:
            raise ValueError("Período invertido.")
        periodo_padrao = False
    except (KeyError, ValueError, TypeError):
        # Fallback: se o Gemma escorregar no formato, usa a semana.
        inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(days=7)
        periodo_padrao = True

    return {"inicio": inicio, "fim": fim, "periodo_padrao": periodo_padrao}


def extrair_periodo(pergunta: str) -> tuple[datetime, datetime]:
    """Atalho de extrair_periodo_detalhado(): devolve só (inicio, fim)."""
    periodo = extrair_periodo_detalhado(pergunta)
    return periodo["inicio"], periodo["fim"]


class AgenteVisualizar:
    """Agente de visualização: ocupados, livres e conflitos de um período."""


    def executar(self, inicio: datetime, fim: datetime) -> dict:
        """Busca os eventos do período e devolve a visualização.


        Args:
            inicio: começo do período (sem fuso = horário de config.FUSO).
            fim: fim do período.


        Returns:
            Dicionário com ocupados, livres, conflitos e totais em minutos.


        Raises:
            ValueError: se ``fim`` não for posterior a ``inicio``.


        Escopo OAuth: somente leitura (config.ESCOPO_SOMENTE_LEITURA).
        """
        # As datas vão para o Google já com o fuso do projeto; sem fuso,
        # o listar_eventos as trataria como UTC (3 horas de diferença).
        inicio = normalizar_fuso(inicio)
        fim = normalizar_fuso(fim)


        if fim <= inicio:
            raise ValueError("A data final deve ser posterior à inicial.")


        servico = get_service([config.ESCOPO_SOMENTE_LEITURA])
        eventos_google = listar_eventos(
            servico, inicio.isoformat(), fim.isoformat()
        )


        eventos = [
            evento
            for evento in map(converter_evento_google, eventos_google)
            if evento is not None
        ]


        visualizacao = montar_visualizacao(eventos=eventos, inicio=inicio, fim=fim)


        return visualizacao.model_dump(mode="json")


    def executar_por_texto(self, pergunta: str) -> RespostaAgente:
        """Contrato final do agente: recebe texto e devolve o JSON padrão.

        Fluxo:
            inicio -> extrair_periodo_detalhado(): LLM entende o pedido.
            meio   -> executar(): busca eventos e calcula livres/conflitos.
            fim    -> montar_mensagem(): o código monta o resumo (sem LLM).

        Args:
            pergunta: pedido do usuário em texto livre.

        Returns:
            RespostaAgente com acao "agenda_visualizada" e, em ``dados``,
            ocupados, livres, conflitos e totais em minutos.
        """

        def extrair(texto: str) -> dict:
            periodo = extrair_periodo_detalhado(texto)
            return {
                "inicio": periodo["inicio"].isoformat(),
                "fim": periodo["fim"].isoformat(),
                "periodo_padrao": periodo["periodo_padrao"],
            }

        def executar(extraido: dict) -> ResultadoExecucao:
            inicio = datetime.fromisoformat(extraido["inicio"])
            fim = datetime.fromisoformat(extraido["fim"])
            visualizacao = self.executar(inicio, fim)
            detalhe = {
                "total_eventos": sum(
                    1 for b in visualizacao["ocupados"] if b["tipo"] != "sono"
                ),
                "total_livres": len(visualizacao["livres"]),
                "total_conflitos": len(visualizacao["conflitos"]),
            }
            return ResultadoExecucao(
                dados=visualizacao,
                periodo=Periodo.de(inicio, fim),
                detalhe=detalhe,
            )

        return executar_fluxo(
            agente="visualizar",
            acao_sucesso="agenda_visualizada",
            acao_erro="agenda_nao_visualizada",
            pergunta=pergunta,
            extrair=extrair,
            executar=executar,
            montar_mensagem=montar_mensagem,
        )


def _formatar_horario(texto_iso: str) -> str:
    """Converte '2026-10-29T09:00:00-03:00' em '29/10 09:00'."""
    return datetime.fromisoformat(texto_iso).strftime("%d/%m %H:%M")


def _formatar_dia_inteiro(bloco: dict) -> str:
    """Formata um evento de dia inteiro: '- Feriado (29/10)'.

    O fim é exclusivo (00:00 do dia seguinte), por isso o último dia
    mostrado é o anterior a ele.
    """
    primeiro = datetime.fromisoformat(bloco["inicio"]).date()
    ultimo = (datetime.fromisoformat(bloco["fim"]) - timedelta(seconds=1)).date()
    dias = primeiro.strftime("%d/%m")

    if ultimo != primeiro:
        dias += f" a {ultimo.strftime('%d/%m')}"

    return f"- {bloco['titulo']} ({dias})"


def classificar_agenda(total_minutos_livres: float) -> str:
    """Classifica a agenda pelo total de minutos livres: cheia, média ou livre."""
    if total_minutos_livres <= 60:
        return "cheia"
    if total_minutos_livres <= 240:
        return "média"
    return "livre"


def montar_mensagem(resultado: ResultadoExecucao) -> str:
    """Escreve o resumo da agenda a partir dos dados calculados (sem LLM).

    Usa só o que o código já calculou: período, livres, ocupados (com o sono),
    eventos de dia inteiro e conflitos. Nos conflitos, troca o id do evento
    pelo título. Seções vazias de dia inteiro e de conflitos são omitidas.

    Args:
        resultado: resultado da etapa meio (``dados`` é o dicionário devolvido
            por AgenteVisualizar.executar() e ``periodo`` é o período lido).

    Returns:
        Texto em português com o resumo da agenda.
    """
    dados = resultado.dados
    periodo = resultado.periodo
    total_livres = dados["total_minutos_livres"]

    linhas: list[str] = []

    if periodo is not None:
        linhas.append(
            f"Avaliei o período de {_formatar_horario(periodo.inicio.isoformat())} "
            f"até {_formatar_horario(periodo.fim.isoformat())}."
        )

    linhas.append(
        f"Sua agenda está {classificar_agenda(total_livres)}, "
        f"com {total_livres:.0f} minutos livres."
    )

    livres = [
        f"- {_formatar_horario(livre['inicio'])} até {_formatar_horario(livre['fim'])}"
        for livre in dados["livres"]
    ]
    linhas += ["", "Horários livres:", *(livres or ["- Nenhum"])]

    ocupados = [
        f"- {bloco['titulo']}: {_formatar_horario(bloco['inicio'])} "
        f"até {_formatar_horario(bloco['fim'])}"
        for bloco in dados["ocupados"]
        if bloco["tipo"] != "dia_inteiro"
    ]
    linhas += ["", "Horários ocupados:", *(ocupados or ["- Nenhum"])]

    dia_inteiro = [
        _formatar_dia_inteiro(bloco)
        for bloco in dados["ocupados"]
        if bloco["tipo"] == "dia_inteiro"
    ]
    if dia_inteiro:
        linhas += ["", "Evento de dia inteiro:", *dia_inteiro]

    if dados["conflitos"]:
        titulos = {bloco["id"]: bloco["titulo"] for bloco in dados["ocupados"]}
        conflitos = [
            f"- {' x '.join(titulos.get(i, i) for i in conflito['ids_eventos'])}: "
            f"{_formatar_horario(conflito['inicio_sobreposicao'])} "
            f"até {_formatar_horario(conflito['fim_sobreposicao'])}"
            for conflito in dados["conflitos"]
        ]
        linhas += ["", "Você possui compromissos conflitantes:", *conflitos]

    return "\n".join(linhas)
