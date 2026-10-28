"""
Agente de visualização da agenda.

Busca os eventos do Google Agenda (somente leitura) e calcula ocupados,
livres e conflitos com o core/agenda_engine.py.

Contrato final: recebe o pedido do usuário em texto, extrai o período com o
LLM (PROMPT_EXTRACAO), busca os eventos, calcula a visualização e devolve
um texto em português com o resumo (PROMPT_RESPOSTA).
"""

import json
from datetime import date, datetime, time, timedelta

from destrava.core import config
from destrava.core.agenda_engine import montar_visualizacao, normalizar_fuso
from destrava.core.google_client import get_service, listar_eventos
from destrava.core.llm_client import perguntar
from destrava.prompts.visualizar import PROMPT_EXTRACAO, PROMPT_RESPOSTA


PALAVRAS_DE_ACAO = (
    "exclua", "excluir", "apague", "apagar", "delete", "deletar",
    "crie", "criar", "adicione", "adicionar", "edite", "editar",
    "modifique", "modificar", "remova", "remover",
)


def _pede_acao(pergunta: str) -> bool:
    """Verifica se o usuário está pedindo uma ação (criar/editar/excluir)."""
    texto = pergunta.lower()
    return any(palavra in texto for palavra in PALAVRAS_DE_ACAO)


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


def extrair_periodo(pergunta: str) -> tuple[datetime, datetime]:
    """Usa o LLM para transformar o pedido em um período de datas.

    Args:
        pergunta: pedido do usuário em texto livre.

    Returns:
        Tupla (inicio, fim) já normalizada no fuso do projeto.

    Se o modelo não devolver um JSON válido, usa os próximos 7 dias
    como fallback seguro.
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
        dados = json.loads(resposta)
        inicio = datetime.fromisoformat(dados["inicio"])
        fim = datetime.fromisoformat(dados["fim"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # Fallback: se o Gemma escorregar no formato, usa a semana.
        inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(days=7)

    return normalizar_fuso(inicio), normalizar_fuso(fim)


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

    def executar_por_texto(self, pergunta: str) -> str:
        """Contrato final do agente: recebe texto e devolve texto.

        Fluxo:
            1. Verifica se o pedido é de ação (criar/editar/excluir).
            2. Se for, responde que não tem permissão.
            3. Senão, extrai o período, busca eventos e responde.

        Args:
            pergunta: pedido do usuário em texto livre.

        Returns:
            Texto curto em português com o resumo da agenda.
        """
        if _pede_acao(pergunta):
            return (
                "Não tenho permissão para criar, editar ou excluir eventos. "
                "Por favor, consulte o Agente de Exclusão para realizar essa ação."
            )

        inicio, fim = extrair_periodo(pergunta)
        resultado = self.executar(inicio, fim)
        return responder(pergunta, resultado)


def _formatar_horario(texto_iso: str) -> str:
    """Converte '2026-10-29T09:00:00-03:00' em '29/10 09:00'."""
    return datetime.fromisoformat(texto_iso).strftime("%d/%m %H:%M")


def _formatar_dia_inteiro(bloco: dict) -> str:
    """Formata um evento de dia inteiro: '29/10 (dia inteiro): Feriado'."""
    primeiro = datetime.fromisoformat(bloco["inicio"]).date()
    ultimo = (datetime.fromisoformat(bloco["fim"]) - timedelta(seconds=1)).date()
    dias = primeiro.strftime("%d/%m")

    if ultimo != primeiro:
        dias += f" a {ultimo.strftime('%d/%m')}"

    return f"- {dias} (dia inteiro): {bloco['titulo']}"


def formatar_para_prompt(resultado: dict) -> dict[str, str]:
    """Transforma o resultado do executar() em listas de texto para o prompt."""

    ocupados = [
        f"- {_formatar_horario(b['inicio'])} a {_formatar_horario(b['fim'])}: {b['titulo']}"
        for b in resultado["ocupados"]
        if b["tipo"] != "dia_inteiro"
    ]
    dia_inteiro = [
        _formatar_dia_inteiro(b)
        for b in resultado["ocupados"]
        if b["tipo"] == "dia_inteiro"
    ]
    livres = [
        f"- {_formatar_horario(l['inicio'])} a {_formatar_horario(l['fim'])} "
        f"({l['duracao_minutos']:.0f} min)"
        for l in resultado["livres"]
    ]

    def classificar_agenda(total_livres: int) -> str:
        if total_livres <= 60:
            return "cheia"
        if total_livres <= 240:
            return "média"
        return "curta"

    titulos = {b["id"]: b["titulo"] for b in resultado["ocupados"]}
    conflitos = [
        f"- {' x '.join(titulos.get(i, i) for i in c['ids_eventos'])}: "
        f"{_formatar_horario(c['inicio_sobreposicao'])} a "
        f"{_formatar_horario(c['fim_sobreposicao'])}"
        for c in resultado["conflitos"]
    ]

    total_livres = resultado["total_minutos_livres"]

    return {
        "eventos": "\n".join(ocupados) or "- Nenhum",
        "livres": "\n".join(livres) or "- Nenhum",
        "conflitos": "\n".join(conflitos) or "- Nenhum",
        "dia_inteiro": "\n".join(dia_inteiro) or "- Nenhum",
        "total_livres": f"{total_livres:.0f}",
        "classificacao": classificar_agenda(total_livres),
    }


def responder(pergunta: str, resultado: dict) -> str:
    dados = formatar_para_prompt(resultado)

    quer_livres = _pede_livres(pergunta)
    quer_conflitos = _pede_conflitos(pergunta)
    quer_ocupados = _pede_ocupados(pergunta)

    # Se não pediu nada específico, mostra tudo
    if not (quer_livres or quer_conflitos or quer_ocupados):
        quer_livres = quer_conflitos = quer_ocupados = True

    secoes = []
    if quer_ocupados:
        secoes.append(f"Horários ocupados:\n{dados['eventos']}")
        if dados["dia_inteiro"] != "- Nenhum":
            secoes.append(f"Eventos de dia inteiro:\n{dados['dia_inteiro']}")
    if quer_livres:
        secoes.append(f"Horários livres:\n{dados['livres']}")
        secoes.append(f"Total de minutos livres:\n{dados['total_livres']}")
        secoes.append(f"Classificação da agenda:\n{dados['classificacao']}")
    if quer_conflitos:
        secoes.append(f"Conflitos:\n{dados['conflitos']}")

    contexto = "\n\n".join(secoes)

    prompt = f"""Você é o Agente de Visualização do Destrava.

Responda ao pedido do usuário usando SOMENTE os dados abaixo.
Inclua apenas as seções presentes nos dados — não invente seções que não foram informadas.

Pedido do usuário:
{pergunta}

Dados disponíveis:
{contexto}

Responda em português brasileiro, de forma curta e clara. Não invente nada."""

    return perguntar(prompt)

def _pede_livres(pergunta: str) -> bool:
    texto = pergunta.lower()
    return any(p in texto for p in ("livre", "livres", "disponível", "disponivel", "vago", "vagos"))


def _pede_conflitos(pergunta: str) -> bool:
    texto = pergunta.lower()
    return any(p in texto for p in ("conflit", "sobrepõe", "sobrepoe", "colide", "colidem"))


def _pede_ocupados(pergunta: str) -> bool:
    texto = pergunta.lower()
    return any(p in texto for p in ("ocupado", "ocupados", "compromisso", "compromissos", "evento", "eventos", "agenda"))