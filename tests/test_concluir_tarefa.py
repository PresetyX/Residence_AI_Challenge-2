"""Marcar etapas do plano como concluídas, com um Google Calendar falso."""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.calendario as calendario
from destrava.core import config
from tests.test_calendario_api import ServicoFalso


def _hora(h):
    dia = datetime.now(config.FUSO) + timedelta(days=1)
    return dia.replace(hour=h, minute=0, second=0, microsecond=0).isoformat()


def _evento(identificador, titulo, privado=None):
    evento = {"id": identificador, "summary": titulo, "description": "passos",
              "start": {"dateTime": _hora(9)}, "end": {"dateTime": _hora(10)}}
    if privado:
        evento["extendedProperties"] = {"private": privado}
    return evento


@pytest.fixture
def cenario(monkeypatch):
    servico = ServicoFalso()
    monkeypatch.setattr(calendario, "get_service", lambda escopos: servico)
    app = FastAPI()
    app.include_router(calendario.router)
    return TestClient(app), servico


def test_conclui_a_etapa_sem_apagar_nem_alterar_o_evento(cenario):
    cliente, servico = cenario
    servico.banco["a"] = _evento("a", "[Destrava] Cadastrar gasto (Pomodoro)")
    antes = dict(servico.banco["a"])

    resposta = cliente.post("/calendar/events/a/concluir").json()

    assert resposta["status"] == "sucesso" and resposta["acao"] == "tarefa_concluida"
    assert resposta["dados"]["evento"]["concluido"] is True
    depois = servico.banco["a"]
    assert {k: v for k, v in depois.items() if k != "extendedProperties"} == antes
    assert depois["extendedProperties"] == {"private": {"concluido": "true"}}
    assert cliente.get("/calendar/events").json()["dados"]["eventos"][0]["concluido"] is True


def test_preserva_a_meta_do_plano(cenario):
    cliente, servico = cenario
    servico.banco["a"] = _evento("a", "Estudar", {"meta": "TCC"})

    evento = cliente.post("/calendar/events/a/concluir").json()["dados"]["evento"]

    assert evento["meta"] == "TCC" and evento["concluido"] is True


def test_concluir_duas_vezes_continua_concluida(cenario):
    cliente, servico = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")
    cliente.post("/calendar/events/a/concluir")

    assert cliente.post("/calendar/events/a/concluir").json()["status"] == "sucesso"


def test_compromisso_comum_nao_pode_ser_concluido(cenario):
    cliente, servico = cenario
    servico.banco["a"] = _evento("a", "Dentista")

    resposta = cliente.post("/calendar/events/a/concluir").json()

    assert resposta["status"] == "erro" and "etapas de um plano" in resposta["erro"]["mensagem"]
    assert "extendedProperties" not in servico.banco["a"]


def test_evento_inexistente_responde_404(cenario):
    cliente, _ = cenario
    assert cliente.post("/calendar/events/nada/concluir").status_code == 404


def test_evento_nao_concluido_nao_traz_a_marca(cenario):
    cliente, servico = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")
    assert "concluido" not in cliente.get("/calendar/events/a").json()["dados"]["evento"]
