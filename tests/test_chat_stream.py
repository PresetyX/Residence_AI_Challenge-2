"""Testes da rota POST /chat/stream com um Supervisor falso (sem Ollama nem Google)."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.chat import router


class SupervisorFalso:
    def __init__(self, resposta: dict | Exception):
        self.resposta = resposta
        self.pedidos: list[str] = []

    def executar(self, pedido: str) -> dict:
        self.pedidos.append(pedido)
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta


def _cliente(supervisor: SupervisorFalso) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.supervisor = supervisor
    return TestClient(app)


def _conversar(cliente: TestClient, *mensagens: tuple[str, str]) -> list[dict]:
    resposta = cliente.post("/chat/stream", json={
        "modelo": "gemma-2b",
        "sistema": "regras",
        "mensagens": [{"papel": p, "conteudo": c} for p, c in mensagens],
    })
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(linha) for linha in resposta.text.splitlines() if linha.strip()]


def _texto(linhas: list[dict]) -> str:
    return "".join(linha["valor"] for linha in linhas if linha["tipo"] == "token")


def test_envia_ultima_mensagem_do_usuario_e_devolve_o_texto():
    supervisor = SupervisorFalso({"status": "confirmacao", "acao": "criar",
                                  "mensagem": "Confirma a criação? Responda 'sim' ou 'não'."})
    linhas = _conversar(_cliente(supervisor),
                        ("usuario", "oi"), ("assistente", "Olá!"), ("usuario", "Crie X amanhã das 13h às 14h"))

    assert supervisor.pedidos == ["Crie X amanhã das 13h às 14h"]
    assert linhas[0]["tipo"] == "status"
    assert _texto(linhas) == "Confirma a criação? Responda 'sim' ou 'não'."
    assert not any(linha["tipo"] == "acao_agenda" for linha in linhas)


def test_evento_criado_vira_acao_agenda():
    evento = {"id": "abc", "titulo": "Reunião", "inicio": "2026-11-18T13:00:00-03:00",
              "fim": "2026-11-18T14:00:00-03:00", "link": "https://calendar.google.com/x"}
    linhas = _conversar(_cliente(SupervisorFalso(
        {"status": "sucesso", "acao": "criar", "mensagem": "Evento 'Reunião' criado com sucesso!", "dados": evento}
    )), ("usuario", "sim"))

    acoes = [linha for linha in linhas if linha["tipo"] == "acao_agenda"]
    assert acoes == [{"tipo": "acao_agenda", "acao": "created", "evento": evento}]


def test_cronograma_parcial_envia_os_eventos_que_foram_criados():
    criados = [{"id": "1", "titulo": "A", "inicio": "x", "fim": "y"},
               {"id": "2", "titulo": "B", "inicio": "x", "fim": "y"}]
    linhas = _conversar(_cliente(SupervisorFalso(
        {"status": "parcial", "acao": "planejar", "mensagem": "Parcial.", "dados": {"eventos_criados": criados}}
    )), ("usuario", "sim"))

    assert [linha["evento"]["id"] for linha in linhas if linha["tipo"] == "acao_agenda"] == ["1", "2"]


def test_funcao_indisponivel_sugere_painel_manual():
    linhas = _conversar(_cliente(SupervisorFalso(
        {"status": "indisponivel", "acao": "planejar", "mensagem": "Ainda não."}
    )), ("usuario", "planeje"))
    assert linhas[-1] == {"tipo": "sugerir_painel_manual"}

    linhas = _conversar(_cliente(SupervisorFalso(
        {"status": "indisponivel", "acao": "fora_escopo", "mensagem": "Posso ajudar com a agenda."}
    )), ("usuario", "qual a capital da França?"))
    assert {"tipo": "sugerir_painel_manual"} not in linhas


def test_excecao_no_supervisor_vira_mensagem_e_nao_derruba_o_stream():
    linhas = _conversar(_cliente(SupervisorFalso(RuntimeError("Ollama fora do ar"))), ("usuario", "oi"))
    assert "Ollama fora do ar" in _texto(linhas)


def test_sem_mensagens_e_rejeitado():
    resposta = _cliente(SupervisorFalso({})).post("/chat/stream", json={"mensagens": []})
    assert resposta.status_code == 422
