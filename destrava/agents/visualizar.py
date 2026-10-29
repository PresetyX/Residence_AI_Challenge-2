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


# Palavras que indicam um pedido de criar, editar ou excluir. Este agente é só
# de leitura, então esses pedidos são recusados antes de chamar o LLM.
PALAVRAS_DE_ACAO = (
    "exclua", "excluir", "apague", "apagar", "delete", "deletar",
    "crie", "criar", "adicione", "adicionar", "edite", "editar",
    "modifique", "modificar", "remova", "remover",
)


def _pede_acao(pergunta: str) -> bool:
    """Verifica se o usuário está pedindo uma ação (criar/editar/excluir)."""
    texto = pergunta.lower()  # minúsculas: "Apague" e "apague" contam igual
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
        # Evento com horário. O Google pode mandar "Z" (UTC), que vira "+00:00".
        inicio = datetime.fromisoformat(
            inicio_google["dateTime"].replace("Z", "+00:00")
        )
        fim = datetime.fromisoformat(fim_google["dateTime"].replace("Z", "+00:00"))
        tipo = "evento"
    elif inicio_google.get("date") and fim_google.get("date"):
        # Evento de dia inteiro: só tem a data, então vira 00:00 no fuso do projeto.
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
    # 1. Data de hoje: o modelo não sabe que dia é, e sem ela
    #    "amanhã" não tem como virar uma data.
    hoje = datetime.now(config.FUSO)
    hoje_iso = hoje.date().isoformat()

    # 2. Preenche as lacunas do prompt e pede o período ao LLM.
    prompt = PROMPT_EXTRACAO.format(
        data_de_hoje=hoje_iso,
        fuso=str(config.FUSO),
        pergunta_do_usuario=pergunta,
    )

    resposta = perguntar(prompt)

    # 3. Lê o JSON devolvido e converte o texto em datas.
    try:
        dados = json.loads(resposta)
        inicio = datetime.fromisoformat(dados["inicio"])
        fim = datetime.fromisoformat(dados["fim"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # Fallback: se o Gemma escorregar no formato, usa a semana.
        inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(days=7)

    # 4. Devolve as datas no fuso do projeto.
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
        # 1. Coloca as datas no fuso do projeto. Sem fuso, o listar_eventos
        #    as trataria como UTC (3 horas de diferença).
        inicio = normalizar_fuso(inicio)
        fim = normalizar_fuso(fim)

        if fim <= inicio:
            raise ValueError("A data final deve ser posterior à inicial.")

        # 2. Conecta ao Google só com permissão de leitura e busca os eventos.
        servico = get_service([config.ESCOPO_SOMENTE_LEITURA])
        eventos_google = listar_eventos(
            servico, inicio.isoformat(), fim.isoformat()
        )

        # 3. Converte cada evento do formato do Google para o formato do Bloco,
        #    descartando os que vierem sem início ou fim (None).
        eventos = [
            evento
            for evento in map(converter_evento_google, eventos_google)
            if evento is not None
        ]

        # 4. Calcula ocupados, livres e conflitos (core/agenda_engine.py).
        visualizacao = montar_visualizacao(eventos=eventos, inicio=inicio, fim=fim)

        # 5. Devolve como dicionário, com as datas em texto ISO.
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
        # 1. Pedido de criar, editar ou excluir: recusa sem chamar o LLM.
        if _pede_acao(pergunta):
            return (
                "Não tenho permissão para criar, editar ou excluir eventos. "
                "Por favor, consulte o Agente de Exclusão para realizar essa ação."
            )

        # 2. LLM transforma a pergunta em período ("amanhã" -> datas).
        inicio, fim = extrair_periodo(pergunta)
        # 3. Código busca os eventos e calcula a agenda (sem LLM).
        resultado = self.executar(inicio, fim)
        # 4. LLM escreve a resposta em português usando só os dados calculados.
        return responder(pergunta, resultado)


def _formatar_horario(texto_iso: str) -> str:
    """Converte '2026-10-29T09:00:00-03:00' em '29/10 09:00'."""
    return datetime.fromisoformat(texto_iso).strftime("%d/%m %H:%M")


def _formatar_dia_inteiro(bloco: dict) -> str:
    """Formata um evento de dia inteiro: '29/10 (dia inteiro): Feriado'."""
    primeiro = datetime.fromisoformat(bloco["inicio"]).date()
    # O fim é 00:00 do dia seguinte (exclusivo): tira 1 segundo para achar o último dia.
    ultimo = (datetime.fromisoformat(bloco["fim"]) - timedelta(seconds=1)).date()
    dias = primeiro.strftime("%d/%m")

    if ultimo != primeiro:
        dias += f" a {ultimo.strftime('%d/%m')}"

    return f"- {dias} (dia inteiro): {bloco['titulo']}"


def formatar_para_prompt(resultado: dict) -> dict[str, str]:
    """Transforma o resultado do executar() em listas de texto para o prompt."""

    # O Gemma entende melhor uma lista legível ("- 09:00 às 10:00: Reunião")
    # do que JSON. Eventos com horário e de dia inteiro ficam em listas separadas.
    ocupados = [
        f"- {_formatar_horario(b['inicio'])} às {_formatar_horario(b['fim'])}: {b['titulo']}"
        for b in resultado["ocupados"]
        if b["tipo"] != "dia_inteiro"
    ]
    dia_inteiro = [
        _formatar_dia_inteiro(b)
        for b in resultado["ocupados"]
        if b["tipo"] == "dia_inteiro"
    ]
    livres = [
        f"- {_formatar_horario(l['inicio'])} às {_formatar_horario(l['fim'])} "
        f"({l['duracao_minutos']:.0f} min)"
        for l in resultado["livres"]
    ]

    # Classifica a agenda pelo total de minutos livres no período.
    def classificar_agenda(total_livres: int) -> str:
        if total_livres <= 60:
            return "cheia"
        if total_livres <= 240:
            return "média"
        return "curta"

    # Nos conflitos, troca o id do evento pelo título, para a resposta citar nomes.
    titulos = {b["id"]: b["titulo"] for b in resultado["ocupados"]}
    conflitos = [
        f"- {' x '.join(titulos.get(i, i) for i in c['ids_eventos'])}: "
        f"{_formatar_horario(c['inicio_sobreposicao'])} a "
        f"{_formatar_horario(c['fim_sobreposicao'])}"
        for c in resultado["conflitos"]
    ]

    total_livres = resultado["total_minutos_livres"]

    # "- Nenhum" quando a lista está vazia: sem isso, o modelo tende a
    # inventar algo para preencher a seção.
    return {
        "eventos": "\n".join(ocupados) or "- Nenhum",
        "livres": "\n".join(livres) or "- Nenhum",
        "conflitos": "\n".join(conflitos) or "- Nenhum",
        "dia_inteiro": "\n".join(dia_inteiro) or "- Nenhum",
        "total_livres": f"{total_livres:.0f}",
        "classificacao": classificar_agenda(total_livres),
    }


# Detectores de intenção: cada um diz se a pergunta fala de livres, conflitos
# ou ocupados, procurando palavras-chave. Se nenhum disparar, o responder
# mostra tudo (pergunta geral, ex.: "como está minha agenda?").
def _pede_livres(pergunta: str) -> bool:
    texto = pergunta.lower()
    return any(p in texto for p in ("livre", "livres", "disponível", "disponivel", "vago", "vagos"))


def _pede_conflitos(pergunta: str) -> bool:
    texto = pergunta.lower()
    # "conflit" sem o final pega conflito, conflitos e conflitante.
    return any(p in texto for p in ("conflit", "sobrepõe", "sobrepoe", "colide", "colidem"))


def _pede_ocupados(pergunta: str) -> bool:
    texto = pergunta.lower()
    # "agenda" não entra: aparece em quase toda pergunta e ativaria esta seção sempre.
    return any(p in texto for p in ("ocupado", "ocupados", "compromisso", "compromissos", "evento", "eventos"))


def responder(pergunta: str, resultado: dict) -> str:
    """Pede ao LLM uma resposta em português usando só os dados calculados.

    O próprio código escolhe quais seções enviar ao modelo (livres, ocupados
    e/ou conflitos), conforme as palavras da pergunta. Assim o modelo só
    recebe o que o usuário pediu e não tem como mostrar o resto.

    Args:
        pergunta: pedido do usuário em texto livre.
        resultado: dicionário devolvido por AgenteVisualizar.executar().

    Returns:
        Texto curto em português respondendo ao pedido.

    Raises:
        ErroLLM: se o modelo não responder.
    """
    # 1. Transforma os dados em listas de texto.
    dados = formatar_para_prompt(resultado)

    # 2. Descobre, por palavras-chave, o que o usuário quer ver.
    quer_livres = _pede_livres(pergunta)
    quer_conflitos = _pede_conflitos(pergunta)
    quer_ocupados = _pede_ocupados(pergunta)

    # Se não pediu nada específico, mostra tudo
    if not (quer_livres or quer_conflitos or quer_ocupados):
        quer_livres = quer_conflitos = quer_ocupados = True

    # 3. Monta o contexto só com as seções pedidas.
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

    # 4. Preenche o PROMPT_RESPOSTA (prompts/visualizar.py) e pede a resposta ao LLM.
    prompt = PROMPT_RESPOSTA.format(
        pergunta_do_usuario=pergunta,
        contexto=contexto,
    )

    return perguntar(prompt)