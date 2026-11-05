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

from datetime import datetime

from pydantic import ValidationError

from destrava.core import config
from destrava.core.google_client import get_service
from destrava.core.models import (
    ErroInfo,
    Etapa,
    Fluxo,
    PedidoCriacao,
    Periodo,
    RespostaAgente,
)


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


def _periodo_confere(
    pedido: PedidoCriacao, inicio_google: str | None, fim_google: str | None
) -> bool:
    """Diz se o início e o fim devolvidos pelo Google são os que foram pedidos."""
    if not inicio_google or not fim_google:
        return False

    inicio = datetime.fromisoformat(inicio_google.replace("Z", "+00:00"))
    fim = datetime.fromisoformat(fim_google.replace("Z", "+00:00"))
    return inicio == pedido.inicio and fim == pedido.fim


class AgenteCriar:
    """Agente responsável por criar eventos no Google Calendar."""

    def executar_json(self, entrada: dict | str) -> dict:
        """Recebe o evento em JSON, cria na agenda e devolve JSON (sem LLM).

        Args:
            entrada: dict ou string JSON com "titulo", "inicio" e "fim"
                (ISO 8601). Datas sem fuso valem no horário de config.FUSO.

        Returns:
            Dicionário com status, acao, periodo, dados, fluxo e erro (o mesmo
            formato do agente de visualização).
            - Sucesso: status "sucesso", periodo do evento e dados com o
              "evento" criado (id, titulo, inicio, fim e link), com as três
              etapas do fluxo "ok".
            - Erro: status "erro" e erro {tipo, mensagem}. A etapa que falhou
              fica "erro" no fluxo e as seguintes ficam "pendente". Pedido
              inválido não chama o Google, e nada é criado.

        Escopo OAuth: calendar (config.ESCOPO_CALENDARIO).
        """
        # 0. Cria o fluxo com as 3 etapas ainda pendentes.
        fluxo = Fluxo(
            inicio=Etapa(etapa="validacao"),
            meio=Etapa(etapa="google_calendar"),
            fim=Etapa(etapa="conferencia"),
        )

        # 1. INÍCIO: valida o pedido.
        try:
            if isinstance(entrada, str):
                pedido = PedidoCriacao.model_validate_json(entrada)
            else:
                pedido = PedidoCriacao.model_validate(entrada)
        except ValidationError as erro:
            fluxo.inicio.status = "erro"
            return RespostaAgente(
                status="erro",
                acao="evento_nao_criado",
                fluxo=fluxo,
                erro=ErroInfo(tipo=type(erro).__name__, mensagem=str(erro)),
            ).model_dump(mode="json")

        fluxo.inicio.status = "ok"
        fluxo.inicio.detalhe = {
            "titulo": pedido.titulo,
            "inicio": pedido.inicio.isoformat(),
            "fim": pedido.fim.isoformat(),
        }

        # 2. Período do evento (vale para sucesso e para erro no meio).
        periodo = Periodo(
            inicio=pedido.inicio,
            fim=pedido.fim,
            duracao_minutos=(pedido.fim - pedido.inicio).total_seconds() / 60,
        )

        # 3. MEIO: cria o evento no Google Calendar.
        try:
            criado = self.executar(
                {
                    "titulo": pedido.titulo,
                    "inicio": pedido.inicio.isoformat(),
                    "fim": pedido.fim.isoformat(),
                }
            )
        except Exception as erro:
            fluxo.meio.status = "erro"
            return RespostaAgente(
                status="erro",
                acao="evento_nao_criado",
                periodo=periodo,
                fluxo=fluxo,
                erro=ErroInfo(tipo=type(erro).__name__, mensagem=str(erro)),
            ).model_dump(mode="json")

        fluxo.meio.status = "ok"
        fluxo.meio.detalhe = {"evento_id": criado["id"]}

        # 4. FIM: confere se o período devolvido pelo Google é o que foi pedido.
        inicio_google = criado.get("start", {}).get("dateTime")
        fim_google = criado.get("end", {}).get("dateTime")
        fluxo.fim.status = "ok"
        fluxo.fim.detalhe = {
            "periodo_confere": _periodo_confere(pedido, inicio_google, fim_google)
        }

        # 5. Sucesso.
        return RespostaAgente(
            status="sucesso",
            acao="evento_criado",
            periodo=periodo,
            dados={
                "evento": {
                    "id": criado["id"],
                    "titulo": criado.get("summary", pedido.titulo),
                    "inicio": inicio_google or pedido.inicio.isoformat(),
                    "fim": fim_google or pedido.fim.isoformat(),
                    "link": criado.get("htmlLink"),
                }
            },
            fluxo=fluxo,
        ).model_dump(mode="json")

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
