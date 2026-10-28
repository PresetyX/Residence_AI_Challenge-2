"""
Agente de visualização da agenda.

Busca os eventos do Google Agenda (somente leitura) e calcula ocupados,
livres e conflitos com o core/agenda_engine.py.

Estado atual: recebe o período (datas) e devolve um dicionário.
Ainda falta a parte do LLM (extrair o período do pedido em texto e
redigir a resposta final), para chegar ao contrato "texto entra, texto sai".
"""

from datetime import date, datetime, time, timedelta

from destrava.core import config
from destrava.core.agenda_engine import montar_visualizacao, normalizar_fuso
from destrava.core.google_client import get_service, listar_eventos
from destrava.core.llm_client import perguntar
from destrava.prompts.visualizar import PROMPT_RESPOSTA


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

def _formatar_horario(texto_iso: str) -> str:
    """Converte '2026-10-29T09:00:00-03:00' em '29/10 09:00'."""
    return datetime.fromisoformat(texto_iso).strftime("%d/%m %H:%M")


def _formatar_dia_inteiro(bloco: dict) -> str:
    """Formata um evento de dia inteiro: '29/10 (dia inteiro): Feriado'.

    O fim é exclusivo (00:00 do dia seguinte), por isso o último dia
    mostrado é o anterior a ele.
    """
    primeiro = datetime.fromisoformat(bloco["inicio"]).date()
    ultimo = (datetime.fromisoformat(bloco["fim"]) - timedelta(seconds=1)).date()
    dias = primeiro.strftime("%d/%m")

    if ultimo != primeiro:
        dias += f" a {ultimo.strftime('%d/%m')}"

    return f"- {dias} (dia inteiro): {bloco['titulo']}"


def formatar_para_prompt(resultado: dict) -> dict[str, str]:
    """Transforma o resultado do executar() em listas de texto para o prompt.

    O Gemma entende melhor uma lista legível do que JSON. Nos conflitos,
    troca o id do evento pelo título, para a resposta citar nomes.
    Eventos de dia inteiro aparecem marcados com "(dia inteiro)".
    """
    ocupados = [
        _formatar_dia_inteiro(b)
        if b["tipo"] == "dia_inteiro"
        else f"- {_formatar_horario(b['inicio'])} a {_formatar_horario(b['fim'])}: {b['titulo']}"
        for b in resultado["ocupados"]
    ]
    livres = [
        f"- {_formatar_horario(l['inicio'])} a {_formatar_horario(l['fim'])} "
        f"({l['duracao_minutos']:.0f} min)"
        for l in resultado["livres"]
    ]

    titulos = {b["id"]: b["titulo"] for b in resultado["ocupados"]}
    conflitos = [
        f"- {' x '.join(titulos.get(i, i) for i in c['ids_eventos'])}: "
        f"{_formatar_horario(c['inicio_sobreposicao'])} a "
        f"{_formatar_horario(c['fim_sobreposicao'])}"
        for c in resultado["conflitos"]
    ]

    return {
        "eventos": "\n".join(ocupados) or "- Nenhum",
        "livres": "\n".join(livres) or "- Nenhum",
        "conflitos": "\n".join(conflitos) or "- Nenhum",
    }


def responder(pergunta: str, resultado: dict) -> str:
    """Pede ao LLM uma resposta em português usando só os dados calculados.

    Args:
        pergunta: o pedido do usuário, em texto.
        resultado: o dicionário devolvido por AgenteVisualizar.executar().

    Returns:
        Texto curto em português explicando a agenda.

    Raises:
        ErroLLM: se o modelo não responder.
    """
    prompt = PROMPT_RESPOSTA.format(
        pergunta_do_usuario=pergunta,
        **formatar_para_prompt(resultado),
    )
    return perguntar(prompt)