"""
Agente de criação de eventos no Google Calendar.

Segue a mesma lógica do agente de visualização: recebe um JSON e devolve um
JSON, sem usar LLM.

    executar_json(entrada) -> recebe o evento em JSON ({"titulo", "inicio",
                              "fim"}), valida com o PedidoCriacao
                              (core/models.py), cria o evento no Google
                              Calendar e devolve o evento criado em JSON.

Chamado pelo Supervisor do Destrava.
Escopo OAuth: calendar (escrita).
"""

from pydantic import ValidationError

from destrava.core import config
from destrava.core.google_client import get_service
from destrava.core.models import PedidoCriacao


def validar_dados_evento(dados: dict) -> dict:
    """
    Valida os dados recebidos para criar um evento.

    As regras ficam no PedidoCriacao (core/models.py): título obrigatório,
    início anterior ao fim e nada no passado. Datas sem fuso são consideradas
    no horário de config.FUSO.

    Args:
        dados (dict): Dicionário contendo título, início e fim.

    Returns:
        dict: Dados validados com datas (texto ISO 8601) no fuso do projeto.

    Raises:
        ValueError: Se algum campo estiver ausente,
            inválido ou com horário inconsistente.
    """
    try:
        pedido = PedidoCriacao.model_validate(dados)
    except ValidationError as erro:
        mensagens = [
            detalhe["msg"].removeprefix("Value error, ")
            for detalhe in erro.errors(include_url=False, include_context=False)
        ]
        raise ValueError(" ".join(dict.fromkeys(mensagens))) from erro

    return {
        "titulo": pedido.titulo,
        "inicio": pedido.inicio.isoformat(),
        "fim": pedido.fim.isoformat(),
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


class AgenteCriar:
    """Agente responsável por criar eventos no Google Calendar."""

    def executar_json(self, entrada: dict | str) -> dict:
        """Recebe o evento em JSON, cria na agenda e devolve JSON (sem LLM).

        Args:
            entrada: dict ou string JSON com "titulo", "inicio" e "fim"
                (ISO 8601). Datas sem fuso valem no horário de config.FUSO.

        Returns:
            {"evento": {"id", "titulo", "inicio", "fim", "link"}} se o evento
            foi criado, ou {"erro": "Pedido inválido", "detalhes": [...]}
            se o pedido não passar na validação (nada é criado).

        Raises:
            RuntimeError: Se a API não retornar o ID do evento.
            HttpError: Se a API do Google retornar um erro.

        Escopo OAuth: calendar (config.ESCOPO_CALENDARIO).
        """
        try:
            if isinstance(entrada, str):
                pedido = PedidoCriacao.model_validate_json(entrada)
            else:
                pedido = PedidoCriacao.model_validate(entrada)
        except ValidationError as erro:
            return {
                "erro": "Pedido inválido",
                "detalhes": erro.errors(include_url=False, include_context=False),
            }

        criado = self.executar(
            {
                "titulo": pedido.titulo,
                "inicio": pedido.inicio.isoformat(),
                "fim": pedido.fim.isoformat(),
            }
        )

        return {
            "evento": {
                "id": criado["id"],
                "titulo": criado.get("summary", pedido.titulo),
                "inicio": criado.get("start", {}).get(
                    "dateTime", pedido.inicio.isoformat()
                ),
                "fim": criado.get("end", {}).get("dateTime", pedido.fim.isoformat()),
                "link": criado.get("htmlLink"),
            }
        }

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
