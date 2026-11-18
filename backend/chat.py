"""Rota POST /chat/stream: o chat do frontend conversando com o Supervisor.

Contrato (frontend/src/services/inference-service.ts):
    Entrada: {"modelo": str, "sistema": str, "mensagens": [{"papel", "conteudo"}]}
    Saída:   NDJSON, um objeto por linha:
        {"tipo": "status", "valor": "..."}            progresso antes da resposta
        {"tipo": "token", "valor": "..."}             pedaço do texto da resposta
        {"tipo": "acao_agenda", "acao": "created", "evento": {...}}
        {"tipo": "sugerir_painel_manual"}             a IA não fez o pedido; oferecer o painel

O Supervisor interpreta só a última mensagem do usuário (ele não usa histórico)
e guarda um único estado de confirmação ("sim"/"não"). Por isso existe uma
instância por processo do backend, protegida por um lock: serve para uso local,
uma pessoa por backend. O "modelo" do seletor do frontend é traduzido para uma
tag do Ollama por config.MODELOS_CHAT; um id desconhecido usa config.MODELO.
"""

import json
import re
import threading
from collections.abc import Iterator
from functools import partial
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config
from destrava.core.llm_client import perguntar

router = APIRouter()

_lock = threading.Lock()


class MensagemChat(BaseModel):
    papel: Literal["usuario", "assistente"]
    conteudo: str


class ChatRequest(BaseModel):
    modelo: str = ""
    sistema: str = ""
    mensagens: list[MensagemChat] = Field(min_length=1)


def _supervisor(request: Request) -> AgenteSupervisor:
    """Cria o Supervisor na primeira mensagem (e não ao subir o servidor)."""
    estado = request.app.state
    if getattr(estado, "supervisor", None) is None:
        estado.supervisor = AgenteSupervisor(planejador=getattr(estado, "planejador", None))
    return estado.supervisor


def _linha(objeto: dict) -> str:
    return json.dumps(objeto, ensure_ascii=False) + "\n"


def _eventos_criados(resposta: dict) -> list[dict]:
    if resposta.get("status") not in ("sucesso", "parcial"):
        return []
    dados = resposta.get("dados")
    if resposta.get("acao") == "criar" and isinstance(dados, dict) and dados.get("id"):
        return [dados]
    if isinstance(dados, dict) and isinstance(dados.get("eventos_criados"), list):
        return [evento for evento in dados["eventos_criados"] if isinstance(evento, dict)]
    return []


def modelo_ollama(modelo_frontend: str) -> str:
    """Tag do Ollama para o id do seletor do frontend."""
    return config.MODELOS_CHAT.get(modelo_frontend, config.MODELO)


def respostas_do_supervisor(
    supervisor: AgenteSupervisor, pedido: str, modelo: str | None = None
) -> Iterator[str]:
    """Executa o pedido e devolve as linhas NDJSON da resposta."""
    yield _linha({"tipo": "status", "valor": f"Consultando o modelo {modelo or config.MODELO}…"})

    with _lock:
        if modelo:
            supervisor.consultar_llm = partial(perguntar, modelo=modelo)
        try:
            resposta = supervisor.executar(pedido)
        except Exception as erro:  # o Supervisor não deveria lançar, mas não derrube o stream
            resposta = {"status": "erro", "acao": "interpretar", "mensagem": f"Falha no Supervisor: {erro}"}

    mensagem = str(resposta.get("mensagem") or "Não consegui responder agora.")
    for pedaco in re.findall(r"\S+\s*|\s+", mensagem):
        yield _linha({"tipo": "token", "valor": pedaco})

    for evento in _eventos_criados(resposta):
        yield _linha({"tipo": "acao_agenda", "acao": "created", "evento": evento})

    # Pedido que o Supervisor ainda não faz (editar, excluir...): oferecer o painel manual.
    if resposta.get("status") == "indisponivel" and resposta.get("acao") != "fora_escopo":
        yield _linha({"tipo": "sugerir_painel_manual"})


@router.post("/chat/stream")
def chat_stream(corpo: ChatRequest, request: Request) -> StreamingResponse:
    pedido = next(
        (m.conteudo for m in reversed(corpo.mensagens) if m.papel == "usuario"),
        "",
    )
    supervisor = _supervisor(request)
    return StreamingResponse(
        respostas_do_supervisor(supervisor, pedido, modelo_ollama(corpo.modelo)),
        media_type="application/x-ndjson",
    )


# ---------------------------------------------------------------------------
# Agendamento de um plano do Planejador (POST /projetos) na agenda.
#
#   POST /projetos/agendar {projeto, prazo, tarefas, meta?}
#       -> Supervisor.preparar_agendamento: classifica o prazo (tranquilo,
#          corrido, impossivel) e devolve a prévia dos eventos, sem criar nada.
#   POST /projetos/agendar/confirmar {confirmado}
#       -> Supervisor.confirmar_agendamento: cria os eventos da prévia.
# ---------------------------------------------------------------------------


class AgendarRequest(BaseModel):
    projeto: str
    prazo: str
    tarefas: list[dict] = Field(min_length=1)
    # Meta do plano (frontend: planGoal), gravada em cada evento criado.
    meta: str | None = None


class ConfirmarRequest(BaseModel):
    confirmado: bool


@router.post("/projetos/agendar")
def agendar_projeto(corpo: AgendarRequest, request: Request) -> dict:
    supervisor = _supervisor(request)
    with _lock:
        # Um plano novo substitui um evento avulso que estava esperando "sim".
        supervisor.evento_pendente = None
        resposta = supervisor.preparar_agendamento(corpo.projeto, corpo.prazo, corpo.tarefas)
        if resposta.get("status") == "confirmacao" and corpo.meta:
            for evento in supervisor.cronograma_pendente or []:
                evento["meta"] = corpo.meta
    return resposta


@router.post("/projetos/agendar/confirmar")
def confirmar_agendamento(corpo: ConfirmarRequest, request: Request) -> dict:
    supervisor = _supervisor(request)
    with _lock:
        # Os eventos criados voltam com a "meta" (o agente criar a devolve).
        return supervisor.confirmar_agendamento(corpo.confirmado)
