"""
Agente de visualização da agenda.

Busca os eventos do Google Agenda (somente leitura) e calcula ocupados,
livres e conflitos com o core/agenda_engine.py.

Contrato: recebe um JSON com o período ("inicio" e "fim") e devolve um JSON
com status, acao, periodo, dados, fluxo e erro. Não usa LLM.
"""

from datetime import date, datetime, time

from pydantic import ValidationError

from destrava.core import config
from destrava.core.agenda_engine import montar_visualizacao, normalizar_fuso
from destrava.core.google_client import get_service, listar_eventos
from destrava.core.models import (
    ErroInfo,
    Etapa,
    Fluxo,
    PedidoVisualizacao,
    Periodo,
    RespostaAgente,
)


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


class AgenteVisualizar:
    """Agente de visualização: ocupados, livres e conflitos de um período."""

    def executar_json(
        self, entrada: dict | str, incluir_ocupados: bool = False
    ) -> dict:
        """Recebe o período em JSON e devolve os horários livres em JSON.

        Args:
            entrada: dict ou string JSON com "inicio" e "fim" (ISO 8601).
                Se "fim" for igual a "inicio", o período vira um dia inteiro.

        Returns:
            Dicionário com status, acao, periodo, dados, fluxo e erro.
            - Sucesso: status "sucesso", periodo e dados (livres e
              total_minutos_livres), com as três etapas do fluxo "ok".
            - Erro: status "erro" e erro {tipo, mensagem}. A etapa que falhou
              fica "erro" no fluxo e as seguintes ficam "pendente".
            incluir_ocupados: inclui os blocos ocupados em ``dados`` quando
                verdadeiro. O padrão preserva o contrato original.
        """
        # 0. Cria o fluxo com as 3 etapas ainda pendentes.
        fluxo = Fluxo(
            inicio=Etapa(etapa="validacao"),
            meio=Etapa(etapa="google_calendar"),
            fim=Etapa(etapa="calculo")
        )
        # 1. INÍCIO: valida o pedido.
        try:
            if isinstance(entrada, str):
                pedido = PedidoVisualizacao.model_validate_json(entrada)
            else:
                pedido = PedidoVisualizacao.model_validate(entrada)
        except ValidationError as erro:
            fluxo.inicio.status = "erro"
            return RespostaAgente(
                status="erro", acao="agenda_nao_visualizada", fluxo=fluxo,
                erro=ErroInfo(tipo=type(erro).__name__, mensagem=str(erro)),
            ).model_dump(mode="json")

        fluxo.inicio.status = "ok"
        fluxo.inicio.detalhe = {"inicio": pedido.inicio.isoformat(), "fim": pedido.fim.isoformat()}

        # 2. Período no fuso do projeto (vale para sucesso e para erro no meio).
        inicio = normalizar_fuso(pedido.inicio)
        fim = normalizar_fuso(pedido.fim)
        periodo = Periodo(inicio=inicio, fim=fim, duracao_minutos=(fim - inicio).total_seconds() / 60)

        # 3. MEIO + FIM: busca no Google e calcula
        try:
            resultado = self.executar(inicio, fim)
        except Exception as erro:
            fluxo.meio.status = "erro"
            return RespostaAgente(
                status="erro", acao="agenda_nao_visualizada", periodo=periodo, fluxo=fluxo,
                erro=ErroInfo(tipo=type(erro).__name__, mensagem=str(erro)),
            ).model_dump(mode="json")

        fluxo.meio.status = "ok"
        fluxo.fim.status = "ok"

        # 4. Sucesso. Por enquanto só livres; ocupados e conflitos ficam de fora.
        dados = {
            "livres": resultado["livres"],
            "total_minutos_livres": resultado["total_minutos_livres"],
        }
        if incluir_ocupados:
            dados["ocupados"] = resultado["ocupados"]

        return RespostaAgente(
            status="sucesso",
            acao="agenda_visualizada",
            periodo=periodo,
            dados=dados,
            fluxo=fluxo,
        ).model_dump(mode="json")

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
