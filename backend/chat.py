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
uma pessoa por backend. O modelo usado é o de config.MODELO (variável MODELO),
não o "modelo" escolhido no seletor do frontend, cujos ids não são tags do Ollama.
"""

import json
import re
import threading
from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from destrava.agents.supervisor import AgenteSupervisor

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


def respostas_do_supervisor(supervisor: AgenteSupervisor, pedido: str) -> Iterator[str]:
    """Executa o pedido e devolve as linhas NDJSON da resposta."""
    yield _linha({"tipo": "status", "valor": "Consultando o modelo…"})

    with _lock:
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
        respostas_do_supervisor(supervisor, pedido),
        media_type="application/x-ndjson",
    )
