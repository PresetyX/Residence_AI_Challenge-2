"""Confirmação por botões: POST /chat/confirmar (sem Google, Ollama ou rede)."""

import json
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.chat as chat
from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


def _evento():
    dia = datetime.now(config.FUSO).date() + timedelta(days=1)
    return {
        "titulo": "Reunião",
        "inicio": datetime.combine(dia, time(10), tzinfo=config.FUSO).isoformat(),
        "fim": datetime.combine(dia, time(11), tzinfo=config.FUSO).isoformat(),
    }


@pytest.fixture
def cenario(monkeypatch):
    salvos = []
    monkeypatch.setattr(chat, "salvar_storypoints_eventos", salvos.extend)
    criador = MagicMock()
    criador.executar_json.side_effect = lambda e: {"status": "sucesso", "dados": {"evento": {"id": "1", **e}}}
    llm = MagicMock()
    supervisor = AgenteSupervisor(visualizador=MagicMock(), criador=criador, consultar_llm=llm)
    supervisor.verificar_disponibilidade = MagicMock(return_value=True)
    monkeypatch.setattr(chat, "perguntar", llm)
    app = FastAPI()
    app.include_router(chat.router)
    app.state.supervisor = supervisor
    return TestClient(app), supervisor, criador, llm, salvos


def _linhas(resposta):
    assert resposta.status_code == 200
    return [json.loads(linha) for linha in resposta.text.splitlines()]


def _tipos(linhas):
    return [linha["tipo"] for linha in linhas if linha["tipo"] not in ("token", "status")]


def _texto(linhas):
    return "".join(linha["valor"] for linha in linhas if linha["tipo"] == "token")


def _digitar(cliente, texto):
    return _linhas(cliente.post("/chat/stream", json={"mensagens": [{"papel": "usuario", "conteudo": texto}]}))


@pytest.mark.parametrize("texto", ["sim", "não", "pode criar", "quero cancelar", "oi"])
def test_texto_digitado_nao_confirma_nem_cancela(cenario, texto):
    cliente, supervisor, criador, llm, _ = cenario
    supervisor.evento_pendente = _evento()

    linhas = _digitar(cliente, texto)

    assert _tipos(linhas) == ["pedir_confirmacao"]
    assert supervisor.evento_pendente is not None
    criador.executar_json.assert_not_called()
    llm.assert_not_called()


def test_botao_sim_cria_o_evento_uma_unica_vez(cenario):
    cliente, supervisor, criador, _, _ = cenario
    supervisor.evento_pendente = _evento()

    linhas = _linhas(cliente.post("/chat/confirmar", json={"confirmado": True}))
    repetido = _linhas(cliente.post("/chat/confirmar", json={"confirmado": True}))

    assert _tipos(linhas) == ["acao_agenda", "fim_conversa"]
    assert "criado com sucesso" in _texto(linhas)
    assert "nada aguardando" in _texto(repetido)
    criador.executar_json.assert_called_once()


def test_botao_nao_cancela_sem_criar(cenario):
    cliente, supervisor, criador, _, _ = cenario
    supervisor.evento_pendente = _evento()

    linhas = _linhas(cliente.post("/chat/confirmar", json={"confirmado": False}))

    assert _tipos(linhas) == ["fim_conversa"]
    assert supervisor.evento_pendente is None
    criador.executar_json.assert_not_called()


def test_botao_sim_no_cronograma_salva_os_story_points(cenario):
    cliente, supervisor, criador, _, salvos = cenario
    supervisor.cronograma_pendente = [{**_evento(), "story_points": 3}]

    linhas = _linhas(cliente.post("/chat/confirmar", json={"confirmado": True}))

    assert _tipos(linhas) == ["acao_agenda", "fim_conversa"]
    assert [e["story_points"] for e in salvos] == [3]


@pytest.mark.parametrize("corpo", [{}, {"confirmado": "sim"}, {"confirmado": 1}])
def test_confirmar_so_aceita_verdadeiro_ou_falso(cenario, corpo):
    cliente, supervisor, criador, _, _ = cenario
    supervisor.evento_pendente = _evento()

    assert cliente.post("/chat/confirmar", json=corpo).status_code == 422
    criador.executar_json.assert_not_called()


def test_previa_pede_os_botoes_sem_mandar_digitar(cenario):
    cliente, supervisor, *_ = cenario
    supervisor.executar = MagicMock(return_value={
        "status": "confirmacao", "acao": "criar",
        "mensagem": "Confirma a criação de 'Reunião'? Responda 'sim' ou 'não'."})

    linhas = _digitar(cliente, "crie uma reunião")

    assert _texto(linhas) == "Confirma a criação de 'Reunião'?"
    assert _tipos(linhas) == ["pedir_confirmacao"]
