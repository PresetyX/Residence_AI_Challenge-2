"""Testes da rota POST /chat/stream com um Supervisor falso (sem Ollama nem Google)."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config
from backend.chat import _supervisor, router


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
        {"status": "indisponivel", "acao": "editar", "mensagem": "Ainda não."}
    )), ("usuario", "mude minha reunião"))
    assert linhas[-1] == {"tipo": "sugerir_painel_manual"}


def test_fora_do_escopo_responde_como_o_planejador_e_pede_o_projeto():
    from destrava.agents.planejador import MENSAGEM_NAO_ENTENDI

    for acao, pedido in (("fora_escopo", "banana com azeite"), ("planejar", "planeje")):
        linhas = _conversar(_cliente(SupervisorFalso(
            {"status": "indisponivel", "acao": acao, "mensagem": "Posso ajudar com a agenda."}
        )), ("usuario", pedido))
        assert _texto(linhas) == MENSAGEM_NAO_ENTENDI
        assert linhas[-1] == {"tipo": "pedir_projeto"}
        assert {"tipo": "sugerir_painel_manual"} not in linhas


def test_excecao_no_supervisor_vira_mensagem_e_nao_derruba_o_stream():
    linhas = _conversar(_cliente(SupervisorFalso(RuntimeError("Ollama fora do ar"))), ("usuario", "oi"))
    assert "Ollama fora do ar" in _texto(linhas)


def test_sem_mensagens_e_rejeitado():
    resposta = _cliente(SupervisorFalso({})).post("/chat/stream", json={"mensagens": []})
    assert resposta.status_code == 422


def test_cada_modelo_do_seletor_vai_para_a_sua_tag_do_ollama(monkeypatch):
    from backend import chat

    usados: list[str | None] = []
    monkeypatch.setattr(chat, "perguntar", lambda prompt, formato=None, modelo=None: usados.append(modelo))

    class SupervisorQueConsulta(SupervisorFalso):
        def executar(self, pedido):
            self.consultar_llm("prompt")
            return {"status": "sucesso", "acao": "visualizar", "mensagem": "ok"}

    cliente = _cliente(SupervisorQueConsulta({}))
    for id_frontend in ("gemma-2b", "gemma-4-26b-a4b-q4_0", "gemma-4-12b-sfp8"):
        cliente.post("/chat/stream", json={"modelo": id_frontend, "mensagens": [{"papel": "usuario", "conteudo": "x"}]})

    assert usados == [chat.config.MODELOS_CHAT[i] for i in ("gemma-2b", "gemma-4-26b-a4b-q4_0", "gemma-4-12b-sfp8")]
    assert len(set(usados)) == 3


def test_evento_criado_ou_cancelado_encerra_a_conversa():
    for resposta in (
        {"status": "sucesso", "acao": "criar", "mensagem": "Criado!", "dados": {"id": "e1", "titulo": "X", "inicio": "2026-11-20T10:00:00-03:00", "fim": "2026-11-20T11:00:00-03:00"}},
        {"status": "cancelado", "acao": "criar", "mensagem": "Criação cancelada."},
    ):
        linhas = _conversar(_cliente(SupervisorFalso(resposta)), ("usuario", "sim"))
        assert linhas[-1] == {"tipo": "fim_conversa"}


def test_edicao_e_exclusao_emitem_acao_e_encerram_conversa():
    evento = {
        "id": "evt-1",
        "titulo": "Reunião",
        "inicio": "2026-11-18T13:00:00-03:00",
        "fim": "2026-11-18T14:00:00-03:00",
    }
    for acao, tipo in (("editar", "updated"), ("excluir", "deleted")):
        linhas = _conversar(_cliente(SupervisorFalso({
            "status": "sucesso",
            "acao": acao,
            "mensagem": "Concluído.",
            "dados": {"evento": evento},
        })), ("usuario", "sim"))

        assert {"tipo": "acao_agenda", "acao": tipo, "evento": evento} in linhas
        assert linhas[-1] == {"tipo": "fim_conversa"}


def test_rota_chat_stream_encaminha_as_quatro_operacoes(monkeypatch):
    amanha = datetime.now(config.FUSO).date() + timedelta(days=1)
    inicio = datetime.combine(amanha, datetime.min.time(), tzinfo=config.FUSO)
    inicio_evento = inicio.replace(hour=10)
    fim_evento = inicio_evento + timedelta(hours=1)
    evento_existente = {
        "id": "evt-10",
        "titulo": "Reunião",
        "inicio": inicio_evento.isoformat(),
        "fim": fim_evento.isoformat(),
        "tipo": "evento",
    }

    visualizador = type("VisualizadorFalso", (), {})()

    def visualizar(entrada, incluir_ocupados=False):
        if incluir_ocupados:
            return {"status": "sucesso", "dados": {"ocupados": [evento_existente]}}
        return {
            "status": "sucesso",
            "dados": {
                "livres": [{"inicio": entrada["inicio"], "fim": entrada["fim"], "duracao_minutos": 60}],
                "total_minutos_livres": 60,
            },
        }

    visualizador.executar_json = visualizar
    criador, editor, excluidor = MagicMock(), MagicMock(), MagicMock()
    criador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {"evento": {"id": "evt-new", "titulo": "Estudo", "inicio": inicio_evento.isoformat(),
                             "fim": fim_evento.isoformat()}},
    }
    editor.executar_json.return_value = {
        "status": "sucesso",
        "dados": {"evento": {**evento_existente, "local": "Biblioteca"}},
    }
    excluidor.executar_json.return_value = {"status": "sucesso"}
    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        criador=criador,
        editor=editor,
        excluidor=excluidor,
    )

    interpretacoes = iter([
        {"acao": "visualizar", "dados": {"inicio": inicio.isoformat(),
                                          "fim": (inicio + timedelta(days=1)).isoformat()}},
        {"acao": "criar", "dados": {"titulo": "Estudo", "inicio": inicio_evento.isoformat(),
                                     "fim": fim_evento.isoformat()}},
        {"acao": "editar", "dados": {"titulo_evento": "Reunião", "data_evento": amanha.isoformat(),
                                      "hora_evento": "10:00", "alteracoes": {"local": "Biblioteca"}}},
        {"acao": "excluir", "dados": {"titulo_evento": "Reunião", "data_evento": amanha.isoformat(),
                                       "hora_evento": "10:00"}},
    ])
    monkeypatch.setattr(
        "backend.chat.perguntar",
        lambda prompt, formato=None, modelo=None: json.dumps(next(interpretacoes)),
    )

    cliente = _cliente(supervisor)

    vista = _conversar(cliente, ("usuario", "Quais horários estão livres amanhã?"))
    assert "livres" in _texto(vista)

    previa_criacao = _conversar(cliente, ("usuario", "Crie estudo amanhã das 10h às 11h"))
    assert _texto(previa_criacao).startswith("Confirma a criação")
    criada = _conversar(cliente, ("usuario", "sim"))
    assert {"tipo": "acao_agenda", "acao": "created",
            "evento": criador.executar_json.return_value["dados"]["evento"]} in criada

    previa_edicao = _conversar(cliente, ("usuario", "Mude a reunião de amanhã para a Biblioteca"))
    assert _texto(previa_edicao).startswith("Confirma a edição")
    editada = _conversar(cliente, ("usuario", "sim"))
    assert {"tipo": "acao_agenda", "acao": "updated",
            "evento": editor.executar_json.return_value["dados"]["evento"]} in editada

    previa_exclusao = _conversar(cliente, ("usuario", "Exclua a reunião de amanhã"))
    assert _texto(previa_exclusao).startswith("Confirma a exclusão")
    excluida = _conversar(cliente, ("usuario", "sim"))
    acao_exclusao = next(linha for linha in excluida if linha.get("acao") == "deleted")
    assert acao_exclusao["evento"]["id"] == evento_existente["id"]
    assert acao_exclusao["evento"]["titulo"] == evento_existente["titulo"]
    assert criador.executar_json.call_count == editor.executar_json.call_count == excluidor.executar_json.call_count == 1


def test_main_monta_rota_chat_stream():
    from backend.main import app

    assert "/chat/stream" in app.openapi()["paths"]


def test_rota_reusa_os_agentes_inicializados_pelo_backend():
    app = FastAPI()
    app.state.visualizador = MagicMock()
    app.state.planejador = MagicMock()
    request = Request({"type": "http", "app": app})

    supervisor = _supervisor(request)

    assert supervisor.visualizador is app.state.visualizador
    assert supervisor.planejador is app.state.planejador


def test_pergunta_pendente_nao_encerra_a_conversa():
    for resposta in (
        {"status": "confirmacao", "acao": "criar", "mensagem": "Confirma?"},
        {"status": "sucesso", "acao": "visualizar", "mensagem": "Você tem 2h livres."},
        {"status": "esclarecimento", "acao": "esclarecer", "mensagem": "Qual horário?"},
    ):
        linhas = _conversar(_cliente(SupervisorFalso(resposta)), ("usuario", "x"))
        assert {"tipo": "fim_conversa"} not in linhas


def test_reiniciar_esquece_as_confirmacoes_pendentes():
    supervisor = SupervisorFalso({"status": "sucesso", "acao": "visualizar", "mensagem": "ok"})
    supervisor.evento_pendente = {"titulo": "Reunião"}
    supervisor.cronograma_pendente = [{"titulo": "Etapa 1"}]
    resposta = _cliente(supervisor).post("/chat/reiniciar")
    assert resposta.status_code == 204
    assert supervisor.evento_pendente is None and supervisor.cronograma_pendente is None
