
"""
Valida dados e realiza a criação de eventos no Google Calendar.

Chamado pelo Supervisor do Destrava.
Utiliza configurações do core e o cliente do Google Calendar.
"""
import json

from destrava.core.google_client import get_service
from destrava.core.llm_client import perguntar
from destrava.prompts.criar import PROMPT_EXTRACAO

from datetime import datetime

from destrava.core import config


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

    resposta = perguntar(prompt).strip()

    # Remove blocos Markdown que o Gemma pode retornar.
    if resposta.startswith("```json"):
        resposta = resposta[7:]
    elif resposta.startswith("```"):
        resposta = resposta[3:]

    if resposta.endswith("```"):
        resposta = resposta[:-3]

    try:
        dados = json.loads(resposta.strip())
    except json.JSONDecodeError as erro:
        raise ValueError(
            "O Gemma não retornou um JSON válido."
        ) from erro

    if not isinstance(dados, dict):
        raise ValueError("O Gemma não retornou um objeto JSON.")

    return validar_dados_evento(dados)


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
