"""Agente de exclusão: recebe um eventId já identificado pelo supervisor.

Contrato público:
    excluir_evento_agenda(id_evento: str, *, id_calendario="primary") -> dict

A localização do evento e a confirmação do usuário acontecem ANTES da
chamada a esta função. O agente não interpreta linguagem natural nem usa LLM.
"""

from __future__ import annotations

from typing import Any

from googleapiclient.errors import HttpError

from ..core import config
from ..core.google_client import get_service

__all__ = ["excluir_evento_agenda"]

def obter_evento(servico, id_evento, *, id_calendario="primary"):
    return servico.events().get(
        calendarId=id_calendario,
        eventId=id_evento
    ).execute()


def excluir_evento(servico, id_evento, *, id_calendario="primary"):
    servico.events().delete(
        calendarId=id_calendario,
        eventId=id_evento
    ).execute()

def excluir_evento_agenda(
    id_evento: str,
    *,
    id_calendario: str = "primary",
) -> dict[str, Any]:
    """Confere a existência e exclui o evento indicado por ID.

    O supervisor deve obter o ``id_evento`` diretamente da API do Calendar,
    resolver ambiguidades e confirmar com o usuário ANTES de invocar esta ação.

    Retorno estruturado permite ao supervisor inspecionar ``sucesso`` e
    responder ao usuário sem precisar interpretar uma mensagem do LLM.
    """
    if not isinstance(id_evento, str) or not id_evento.strip():
        return {
            "sucesso": False,
            "codigo": "id_invalido",
            "mensagem": "O ID do evento deve ser uma string não vazia.",
        }
    if not isinstance(id_calendario, str) or not id_calendario.strip():
        return {
            "sucesso": False,
            "codigo": "calendario_invalido",
            "mensagem": "O ID da agenda deve ser uma string não vazia.",
        }

    id_evento = id_evento.strip()
    id_calendario = id_calendario.strip()

    try:
        servico = get_service([config.ESCOPO_CALENDARIO])
        evento = obter_evento(servico, id_evento, id_calendario=id_calendario)

        if evento.get("status") == "cancelled":
            return {
                "sucesso": False,
                "codigo": "nao_encontrado",
                "id_evento": id_evento,
                "mensagem": "Este evento já está cancelado ou excluído.",
            }

        titulo = evento.get("summary") or "Evento sem título"
        inicio = evento.get("start")  # útil para o supervisor apresentar detalhes

        excluir_evento(servico, id_evento, id_calendario=id_calendario)

        return {
            "sucesso": True,
            "codigo": "excluido",
            "id_evento": id_evento,
            "id_calendario": id_calendario,
            "titulo": titulo,
            "inicio": inicio,
            "mensagem": f"O evento '{titulo}' foi excluído com sucesso.",
        }
    except HttpError as erro:
        status = getattr(erro.resp, "status", None)
        if status in (404, 410):
            codigo = "nao_encontrado"
            mensagem = "O evento não foi encontrado ou já foi excluído."
        elif status == 403:
            codigo = "sem_permissao"
            mensagem = "Não há permissão para consultar ou excluir este evento."
        else:
            codigo = "erro_google_calendar"
            mensagem = f"A API do Google Calendar retornou erro HTTP {status}."
        return {
            "sucesso": False,
            "codigo": codigo,
            "id_evento": id_evento,
            "mensagem": mensagem,
        }
    except Exception as erro:
        return {
            "sucesso": False,
            "codigo": "erro_inesperado",
            "id_evento": id_evento,
            "mensagem": f"Não consegui excluir o evento: {erro}",
        }
