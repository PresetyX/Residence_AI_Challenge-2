"""
Agente de exclusão de eventos no Google Calendar.

Recebe o ID de um evento já identificado (pelo Supervisor ou pelo painel
manual), confere que ele existe e o exclui. Não interpreta linguagem natural
nem usa LLM. A confirmação do usuário acontece ANTES da chamada.

    excluir_evento_agenda(id_evento)  -> dict {sucesso, codigo, mensagem, ...}
    AgenteExcluir().executar_json({"id": ...}) -> JSON padrão dos agentes

Escopo OAuth: calendar (escrita).
"""

from __future__ import annotations

from typing import Any

from googleapiclient.errors import HttpError

from destrava.core import config
from destrava.core.google_client import excluir_evento, get_service, obter_evento
from destrava.core.models import ErroInfo, Etapa, Fluxo, RespostaAgente

__all__ = ["AgenteExcluir", "excluir_evento_agenda"]


def excluir_evento_agenda(
    id_evento: str,
    *,
    id_calendario: str = "primary",
    servico=None,
) -> dict[str, Any]:
    """Confere a existência e exclui o evento indicado por ID.

    Retorno estruturado: o chamador inspeciona ``sucesso`` e ``codigo``
    (excluido, id_invalido, nao_encontrado, sem_permissao,
    erro_google_calendar, erro_inesperado) sem interpretar texto.
    """
    if not isinstance(id_evento, str) or not id_evento.strip():
        return {
            "sucesso": False,
            "codigo": "id_invalido",
            "mensagem": "O ID do evento deve ser uma string não vazia.",
        }
    id_evento = id_evento.strip()

    try:
        servico = servico or get_service([config.ESCOPO_CALENDARIO])
        evento = obter_evento(servico, id_evento, id_calendario=id_calendario)

        if evento.get("status") == "cancelled":
            return {
                "sucesso": False,
                "codigo": "nao_encontrado",
                "id_evento": id_evento,
                "mensagem": "Este evento já está cancelado ou excluído.",
            }

        titulo = evento.get("summary") or "Evento sem título"
        excluir_evento(servico, id_evento, id_calendario=id_calendario)
        return {
            "sucesso": True,
            "codigo": "excluido",
            "id_evento": id_evento,
            "titulo": titulo,
            "inicio": evento.get("start"),
            "mensagem": f"O evento '{titulo}' foi excluído com sucesso.",
        }
    except HttpError as erro:
        status = getattr(erro.resp, "status", None)
        if status in (404, 410):
            codigo, mensagem = "nao_encontrado", "O evento não foi encontrado ou já foi excluído."
        elif status == 403:
            codigo, mensagem = "sem_permissao", "Não há permissão para consultar ou excluir este evento."
        else:
            codigo, mensagem = "erro_google_calendar", f"A API do Google Calendar retornou erro HTTP {status}."
        return {"sucesso": False, "codigo": codigo, "id_evento": id_evento, "mensagem": mensagem}
    except Exception as erro:
        return {
            "sucesso": False,
            "codigo": "erro_inesperado",
            "id_evento": id_evento,
            "mensagem": f"Não consegui excluir o evento: {erro}",
        }


class AgenteExcluir:
    """Agente responsável por excluir eventos no Google Calendar."""

    def __init__(self, servico=None):
        self._servico = servico

    def executar_json(self, entrada: dict) -> dict:
        """Recebe {"id": "..."} e devolve o JSON padrão dos agentes.

        Sucesso: acao "evento_excluido" e dados {"evento_id", "titulo"}.
        Erro: status "erro" e erro {tipo: codigo, mensagem}.
        """
        fluxo = Fluxo(
            inicio=Etapa(etapa="validacao"),
            meio=Etapa(etapa="google_calendar"),
            fim=Etapa(etapa="conferencia"),
        )
        id_evento = entrada.get("id") if isinstance(entrada, dict) else None
        resultado = excluir_evento_agenda(id_evento, servico=self._servico)

        if not resultado["sucesso"]:
            if resultado["codigo"] == "id_invalido":
                fluxo.inicio.status = "erro"
            else:
                fluxo.inicio.status = "ok"
                fluxo.meio.status = "erro"
            return RespostaAgente(
                status="erro",
                acao="evento_nao_excluido",
                fluxo=fluxo,
                erro=ErroInfo(tipo=resultado["codigo"], mensagem=resultado["mensagem"]),
            ).model_dump(mode="json")

        fluxo.inicio.status = fluxo.meio.status = fluxo.fim.status = "ok"
        fluxo.meio.detalhe = {"evento_id": resultado["id_evento"]}
        return RespostaAgente(
            status="sucesso",
            acao="evento_excluido",
            dados={"evento_id": resultado["id_evento"], "titulo": resultado["titulo"]},
            fluxo=fluxo,
        ).model_dump(mode="json")
