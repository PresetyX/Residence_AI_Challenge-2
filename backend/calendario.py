"""Rotas /calendar/events e /auth: o painel Agenda e o login do frontend.

Contrato (frontend/src/services/calendar-service.ts e auth-service.ts). As
respostas de agenda seguem o envelope dos agentes (RespostaAgente):

    GET    /calendar/events?inicio&fim -> dados {eventos: [EventDto]}
    GET    /calendar/events/{id}       -> dados {evento: EventDto}
    POST   /calendar/events            -> dados {evento: EventDto}  (agente criar)
    PUT    /calendar/events/{id}       -> dados {evento: EventDto}  (agente editar)
    DELETE /calendar/events/{id}       -> dados {evento_id}         (agente excluir)

    POST /auth/google/session {consent, scopes} -> {user, grantedScopes}
    POST /auth/logout                            -> 204

O login usa o mesmo OAuth de aplicativo desktop dos agentes (google_client):
na primeira vez o navegador da máquina do backend abre para autorizar e o
token fica salvo em token_calendar.json. É pensado para uso local, uma pessoa
por backend (como o chat).

Erros de agente voltam com status 200 e status "erro" no envelope (o frontend
mostra a mensagem). Falhas de infraestrutura (sem credentials.json, Google fora)
voltam como 503.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from googleapiclient.errors import HttpError
from pydantic import BaseModel

from backend import perfil
from destrava.agents.criar import AgenteCriar
from destrava.agents.editar import AgenteEditar, evento_resumido
from destrava.agents.excluir import AgenteExcluir
from destrava.core import config
from destrava.core.google_client import get_service, listar_eventos, obter_evento
from destrava.core.models import ErroInfo, Etapa, Fluxo, RespostaAgente

router = APIRouter()

# O primeiro get_service pode abrir o navegador: um fluxo OAuth por vez.
_lock_oauth = threading.Lock()

ARQUIVO_CONSENTIMENTO = config.RAIZ_PROJETO / "consentimento.json"


def _servico():
    """Serviço do Google com escopo de escrita (cobre a leitura também)."""
    try:
        with _lock_oauth:
            return get_service([config.ESCOPO_CALENDARIO])
    except FileNotFoundError as erro:
        raise HTTPException(status_code=503, detail=str(erro)) from erro
    except Exception as erro:
        raise HTTPException(
            status_code=503,
            detail=f"Não consegui acessar o Google Agenda: {erro}",
        ) from erro


def _converter_inicio_fim(dto: dict[str, Any]) -> dict[str, Any]:
    """Eventos de dia inteiro vêm só com a data: converte para ISO com fuso."""
    for campo in ("inicio", "fim"):
        valor = dto.get(campo)
        if isinstance(valor, str) and "T" not in valor:
            dia = datetime.fromisoformat(valor).replace(tzinfo=config.FUSO)
            dto[campo] = dia.isoformat()
    return dto


def _envelope_sucesso(acao: str, dados: dict) -> dict:
    fluxo = Fluxo(
        inicio=Etapa(etapa="validacao", status="ok"),
        meio=Etapa(etapa="google_calendar", status="ok"),
        fim=Etapa(etapa="conferencia", status="ok"),
    )
    return RespostaAgente(status="sucesso", acao=acao, dados=dados, fluxo=fluxo).model_dump(mode="json")


def _envelope_erro(acao: str, tipo: str, mensagem: str) -> dict:
    fluxo = Fluxo(
        inicio=Etapa(etapa="validacao", status="ok"),
        meio=Etapa(etapa="google_calendar", status="erro"),
        fim=Etapa(etapa="conferencia"),
    )
    return RespostaAgente(
        status="erro", acao=acao, fluxo=fluxo, erro=ErroInfo(tipo=tipo, mensagem=mensagem)
    ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Agenda
# ---------------------------------------------------------------------------


class EventoEscrita(BaseModel):
    titulo: str
    inicio: str
    fim: str
    descricao: str | None = None
    local: str | None = None
    meta: str | None = None


@router.get("/calendar/events")
def listar(
    inicio: str | None = Query(default=None, description="ISO 8601; padrão: ontem"),
    fim: str | None = Query(default=None, description="ISO 8601; padrão: daqui a 60 dias"),
) -> dict:
    agora = datetime.now(config.FUSO).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio = inicio or (agora - timedelta(days=1)).isoformat()
    fim = fim or (agora + timedelta(days=60)).isoformat()
    servico = _servico()
    try:
        brutos = listar_eventos(servico, inicio, fim)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    except HttpError as erro:
        return _envelope_erro("eventos_nao_listados", "HttpError", f"O Google recusou a consulta: {erro.reason}")
    eventos = [
        _converter_inicio_fim(evento_resumido(bruto))
        for bruto in brutos
        if bruto.get("status") != "cancelled"
    ]
    return _envelope_sucesso("eventos_listados", {"eventos": eventos})


@router.get("/calendar/events/{id_evento}")
def obter(id_evento: str) -> dict:
    servico = _servico()
    try:
        bruto = obter_evento(servico, id_evento)
    except HttpError as erro:
        if getattr(erro.resp, "status", None) in (404, 410):
            raise HTTPException(status_code=404, detail="Agendamento não encontrado.") from erro
        return _envelope_erro("evento_nao_encontrado", "HttpError", str(erro.reason))
    if bruto.get("status") == "cancelled":
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return _envelope_sucesso("evento_obtido", {"evento": _converter_inicio_fim(evento_resumido(bruto))})


@router.post("/calendar/events")
def criar(evento: EventoEscrita) -> dict:
    _servico()  # garante o login (e erro 503 claro) antes de chamar o agente
    entrada = evento.model_dump(exclude_none=True)
    # Strings vazias do formulário não viram campos no Google.
    entrada = {chave: valor for chave, valor in entrada.items() if valor != ""}
    resposta = AgenteCriar().executar_json(entrada)
    if resposta["status"] == "sucesso":
        dados_evento = resposta["dados"]["evento"]
        dados_evento.setdefault("descricao", evento.descricao or "")
        dados_evento.setdefault("local", evento.local or "")
    else:
        resposta["erro"]["mensagem"] = _mensagem_amigavel(resposta["erro"]["mensagem"])
    return resposta


@router.put("/calendar/events/{id_evento}")
def editar(id_evento: str, evento: EventoEscrita) -> dict:
    servico = _servico()
    entrada = evento.model_dump(exclude={"meta"})
    entrada["id"] = id_evento
    # Campos de texto vazios limpam o valor no Google (o formulário envia tudo).
    entrada["descricao"] = entrada.get("descricao") or ""
    entrada["local"] = entrada.get("local") or ""
    resposta = AgenteEditar(servico=servico).executar_json(entrada)
    if resposta["status"] == "sucesso":
        _converter_inicio_fim(resposta["dados"]["evento"])
    else:
        resposta["erro"]["mensagem"] = _mensagem_amigavel(resposta["erro"]["mensagem"])
    return resposta


@router.delete("/calendar/events/{id_evento}")
def excluir(id_evento: str) -> dict:
    servico = _servico()
    return AgenteExcluir(servico=servico).executar_json({"id": id_evento})


def _mensagem_amigavel(mensagem: str) -> str:
    """Erros de validação do pydantic chegam longos: deixa só as frases úteis."""
    if "validation error" not in mensagem:
        return mensagem
    frases = [
        linha.strip().removeprefix("Value error, ").split(" [type=")[0]
        for linha in mensagem.splitlines()
        if linha.strip().startswith("Value error,") or "[type=" in linha
    ]
    return " ".join(dict.fromkeys(f for f in frases if f)) or mensagem


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class SessaoRequest(BaseModel):
    consent: dict[str, Any] = {}
    scopes: list[str] = []


@router.post("/auth/google/session")
def entrar(corpo: SessaoRequest) -> dict:
    servico = _servico()  # abre o navegador para autorizar na primeira vez
    try:
        agenda = servico.calendarList().get(calendarId="primary").execute()
    except HttpError as erro:
        raise HTTPException(status_code=503, detail=f"O Google recusou o acesso: {erro.reason}") from erro

    email = agenda.get("id", "")
    nome = agenda.get("summaryOverride") or agenda.get("summary") or email.split("@")[0]
    if nome == email:
        nome = email.split("@")[0]

    # Guarda o que o usuário aceitou no modal, junto com a sessão.
    registro = {"email": email, "consent": corpo.consent, "registrado_em": datetime.now(config.FUSO).isoformat()}
    ARQUIVO_CONSENTIMENTO.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    # Sono e calibração desta conta passam a valer para a agenda e os story points.
    perfil.ativar_conta(email)

    return {
        "user": {"id": email, "name": nome, "email": email},
        "grantedScopes": ["openid", "email", "profile", config.ESCOPO_CALENDARIO],
    }


@router.post("/auth/logout", status_code=204)
def sair() -> Response:
    # O token do Google continua salvo (token_calendar.json) para o próximo login.
    return Response(status_code=204)
