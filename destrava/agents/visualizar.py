"""
Agente de visualização da agenda.

Busca os eventos do Google Agenda (somente leitura) e calcula ocupados,
livres e conflitos com o core/agenda_engine.py.

Estado atual: recebe o período (datas) e devolve um dicionário.
Ainda falta a parte do LLM (extrair o período do pedido em texto e
redigir a resposta final), para chegar ao contrato "texto entra, texto sai".
"""

from datetime import datetime

from destrava.core import config
from destrava.core.agenda_engine import montar_visualizacao, normalizar_fuso
from destrava.core.google_client import get_service, listar_eventos


def converter_evento_google(evento: dict) -> dict | None:
    """Converte um evento da API do Google para o formato do ``Bloco``.

    Eventos de dia inteiro (que só têm ``date``, sem ``dateTime``) são
    ignorados: costumam ser feriados, aniversários ou lembretes e, por
    padrão, não bloqueiam horário na agenda.

    Returns:
        Dicionário com id, titulo, inicio, fim e tipo, ou None se o evento
        for de dia inteiro ou não tiver início e fim.
    """
    inicio = evento.get("start", {}).get("dateTime")
    fim = evento.get("end", {}).get("dateTime")

    if not inicio or not fim:
        return None

    return {
        "id": evento.get("id", ""),
        "titulo": evento.get("summary", "Compromisso"),
        "inicio": datetime.fromisoformat(inicio.replace("Z", "+00:00")),
        "fim": datetime.fromisoformat(fim.replace("Z", "+00:00")),
        "tipo": "evento",
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
