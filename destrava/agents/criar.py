"""
Agente de criação de eventos no Google Calendar.

Segue o contrato padrão dos agentes (core/resposta.py):

    inicio -> extrair_dados_evento(): o LLM transforma o pedido em JSON
              {"titulo", "inicio", "fim"} e o código valida.
    meio   -> criar_evento_google(): o código cria o evento na API e
              conferir_periodo() checa se o período que voltou do Google é o
              mesmo que foi pedido.
    fim    -> montar_mensagem(): o código escreve a confirmação a partir do
              evento criado (sem LLM).

Contrato final (usado pelo supervisor):
    AgenteCriar().executar_por_texto(pergunta) -> RespostaAgente
    (use .para_dict() ou .para_json() para obter o JSON)

Escopo OAuth: calendar (escrita).
"""

from collections.abc import Callable
from datetime import datetime

from destrava.core import config
from destrava.core.google_client import get_service
from destrava.core.llm_client import extrair_json, perguntar
from destrava.core.resposta import (
    Periodo,
    RespostaAgente,
    ResultadoExecucao,
    executar_fluxo,
)
from destrava.prompts.criar import PROMPT_EXTRACAO


def validar_dados_evento(dados: dict) -> dict:
    """
    Valida os dados recebidos para criar um evento.

    Args:
        dados (dict): Dicionário contendo título, início e fim.

    Returns:
        dict: Dados validados com datas no fuso do projeto.

    Raises:
        ValueError: Se algum campo estiver ausente,
            inválido ou com horário inconsistente.
    """

    titulo = dados.get("titulo")
    inicio = dados.get("inicio")
    fim = dados.get("fim")

    if not isinstance(titulo, str) or not titulo.strip():
        raise ValueError("O título do evento é obrigatório.")

    if not isinstance(inicio, str) or not isinstance(fim, str):
        raise ValueError("Início e fim são obrigatórios.")

    try:
        data_inicio = datetime.fromisoformat(inicio)
        data_fim = datetime.fromisoformat(fim)
    except ValueError as erro:
        raise ValueError("Data ou horário inválido.") from erro

    if data_inicio.tzinfo is None:
        data_inicio = data_inicio.replace(tzinfo=config.FUSO)
    else:
        data_inicio = data_inicio.astimezone(config.FUSO)

    if data_fim.tzinfo is None:
        data_fim = data_fim.replace(tzinfo=config.FUSO)
    else:
        data_fim = data_fim.astimezone(config.FUSO)

    if data_inicio >= data_fim:
        raise ValueError("O início deve ser anterior ao fim.")

    if data_inicio <= datetime.now(config.FUSO):
        raise ValueError("Não é permitido criar eventos no passado.")

    return {
        "titulo": titulo.strip(),
        "inicio": data_inicio.isoformat(),
        "fim": data_fim.isoformat()
    }


def criar_evento_google(dados: dict, servico) -> dict:
    """
    Cria um evento no Google Calendar com dados validados.

    Chamada após a autorização do fluxo de criação.

    Args:
        dados (dict): Dicionário com título, início e fim.
        servico: Serviço autenticado do Google Calendar.

    Returns:
        dict: Evento criado, retornado pela API do Google.

    Raises:
        ValueError: Se os dados do evento forem inválidos.
        RuntimeError: Se a API não retornar o ID do evento.
        HttpError: Se a API do Google retornar um erro.

    Escopo OAuth:
        calendar
    """
    evento = validar_dados_evento(dados)

    corpo = {
        "summary": evento["titulo"],
        "start": {
            "dateTime": evento["inicio"],
            "timeZone": str(config.FUSO)
        },
        "end": {
            "dateTime": evento["fim"],
            "timeZone": str(config.FUSO)
        }
    }

    resultado = servico.events().insert(
        calendarId="primary",
        body=corpo
    ).execute()

    if not resultado.get("id"):
        raise RuntimeError(
            "A API não retornou o ID do evento."
        )

    return resultado


def conferir_periodo(pedido: dict, evento_criado: dict) -> tuple[Periodo, bool]:
    """
    Confere se o período que voltou do Google é o mesmo que foi pedido.

    Args:
        pedido: dados validados (saída de validar_dados_evento).
        evento_criado: evento devolvido pela API do Google.

    Returns:
        (periodo, confere): o período REAL do evento criado (lido da resposta
        do Google) e se ele bate com o início e o fim pedidos.

    Raises:
        RuntimeError: se a API não devolver o início ou o fim do evento.
    """
    inicio_google = evento_criado.get("start", {}).get("dateTime")
    fim_google = evento_criado.get("end", {}).get("dateTime")

    if not inicio_google or not fim_google:
        raise RuntimeError("A API não retornou o período do evento criado.")

    periodo = Periodo.de(
        datetime.fromisoformat(inicio_google.replace("Z", "+00:00")),
        datetime.fromisoformat(fim_google.replace("Z", "+00:00")),
    )
    pedido_inicio = datetime.fromisoformat(pedido["inicio"])
    pedido_fim = datetime.fromisoformat(pedido["fim"])

    confere = periodo.inicio == pedido_inicio and periodo.fim == pedido_fim
    return periodo, confere


def resumir_evento(evento_criado: dict, periodo: Periodo) -> dict:
    """Pega só os campos úteis do evento do Google (para o JSON e o prompt)."""
    return {
        "id": evento_criado["id"],
        "titulo": evento_criado.get("summary", ""),
        "inicio": periodo.inicio.isoformat(),
        "fim": periodo.fim.isoformat(),
        "duracao_minutos": periodo.duracao_minutos,
        "link": evento_criado.get("htmlLink"),
    }


def extrair_dados_evento(pergunta: str) -> dict:
    """
    Extrai e valida os dados de um evento usando o Gemma 2.

    Args:
        pergunta: Solicitação do usuário em linguagem natural.

    Returns:
        dict: Dados do evento validados.

    Raises:
        ValueError: Se a resposta não for um JSON válido
            ou se os dados estiverem incompletos.
    """
    hoje = datetime.now(config.FUSO).date().isoformat()

    prompt = PROMPT_EXTRACAO.format(
        data_de_hoje=hoje,
        fuso=str(config.FUSO),
        pergunta_do_usuario=pergunta
    )

    dados = extrair_json(perguntar(prompt))

    return validar_dados_evento(dados)


def montar_mensagem(resultado: ResultadoExecucao) -> str:
    """
    Escreve a confirmação da criação a partir do evento devolvido pelo Google.

    É código puro (sem LLM): usa só os dados reais do evento criado.

    Args:
        resultado: resultado da etapa meio, com ``dados["evento"]`` e
            ``dados["periodo_confere"]``.

    Returns:
        str: mensagem em português confirmando a criação.

    Raises:
        ValueError: se o evento não tiver a confirmação de criação (id).
    """
    evento = resultado.dados["evento"]

    if not evento.get("id"):
        raise ValueError("O evento não possui confirmação de criação.")

    inicio = datetime.fromisoformat(evento["inicio"])
    fim = datetime.fromisoformat(evento["fim"])
    mensagem = (
        f'Pronto! Criei "{evento["titulo"]}" em {inicio:%d/%m/%Y}, '
        f"das {inicio:%H:%M} às {fim:%H:%M}."
    )

    if not resultado.dados.get("periodo_confere", True):
        mensagem += (
            " Atenção: o período salvo no Google é diferente do pedido, "
            "confira o evento na agenda."
        )

    return mensagem


class AgenteCriar:
    """Agente responsável por criar eventos no Google Calendar."""

    def executar(self, dados: dict) -> dict:
        """
        Cria um evento previamente autorizado pelo Supervisor.

        Args:
            dados: Dicionário com título, início e fim.

        Returns:
            dict: Evento criado, retornado pela API do Google.

        Raises:
            ValueError: Se os dados forem inválidos.
            RuntimeError: Se a API não retornar o ID do evento.
            HttpError: Se a API do Google retornar um erro.

        Escopo OAuth:
            calendar
        """
        servico = get_service([config.ESCOPO_CALENDARIO])

        return criar_evento_google(dados, servico)

    def executar_por_texto(
        self,
        pergunta: str,
        confirmar: Callable[[dict], bool] | None = None,
    ) -> RespostaAgente:
        """
        Contrato final do agente: recebe texto e devolve o JSON padrão.

        Args:
            pergunta: pedido do usuário em texto livre.
            confirmar: opcional. Recebe os dados extraídos e devolve True
                para criar ou False para cancelar (ex.: pedir "CRIAR" no
                terminal). Sem ele, o evento é criado direto.

        Returns:
            RespostaAgente com acao "evento_criado" e, em ``dados``:
                - evento: id, titulo, inicio, fim, duracao_minutos, link
                - periodo_confere: se o período devolvido pelo Google é
                  igual ao pedido
        """

        def executar(pedido: dict) -> ResultadoExecucao:
            evento_criado = self.executar(pedido)
            periodo, confere = conferir_periodo(pedido, evento_criado)
            dados = {
                "evento": resumir_evento(evento_criado, periodo),
                "periodo_confere": confere,
            }
            detalhe = {
                "evento_id": evento_criado["id"],
                "periodo_pedido": {"inicio": pedido["inicio"], "fim": pedido["fim"]},
                "periodo_retornado": {
                    "inicio": periodo.inicio.isoformat(),
                    "fim": periodo.fim.isoformat(),
                },
                "periodo_confere": confere,
            }
            return ResultadoExecucao(dados=dados, periodo=periodo, detalhe=detalhe)

        return executar_fluxo(
            agente="criar",
            acao_sucesso="evento_criado",
            acao_erro="evento_nao_criado",
            pergunta=pergunta,
            extrair=extrair_dados_evento,
            executar=executar,
            montar_mensagem=montar_mensagem,
            confirmar=confirmar,
        )
