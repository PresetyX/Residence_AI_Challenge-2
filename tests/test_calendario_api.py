"""Rotas /calendar/events e /auth do backend, com um Google Calendar falso."""

from __future__ import annotations

import copy
import itertools
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from googleapiclient.errors import HttpError

import backend.calendario as calendario
import destrava.tools.criar as criar
from destrava.core import config


class _Resp(dict):
    def __init__(self, status: int):
        super().__init__()
        self.status = status
        self.reason = "erro"


class _Chamada:
    def __init__(self, funcao):
        self._funcao = funcao

    def execute(self):
        return self._funcao()


class _Eventos:
    def __init__(self, banco: dict):
        self.banco = banco
        self._ids = itertools.count(1)

    def _existente(self, eventId):
        if eventId not in self.banco:
            raise HttpError(_Resp(404), b"not found")
        return self.banco[eventId]

    def list(self, **_):
        itens = sorted(self.banco.values(), key=lambda e: e["start"].get("dateTime", e["start"].get("date")))
        return _Chamada(lambda: {"items": copy.deepcopy(itens)})

    def get(self, calendarId, eventId):
        return _Chamada(lambda: copy.deepcopy(self._existente(eventId)))

    def insert(self, calendarId, body):
        def criar_evento():
            novo = copy.deepcopy(body)
            novo["id"] = f"evt{next(self._ids)}"
            novo["htmlLink"] = f"https://calendar.google.com/event?eid={novo['id']}"
            self.banco[novo["id"]] = novo
            return copy.deepcopy(novo)

        return _Chamada(criar_evento)

    def patch(self, calendarId, eventId, body):
        def aplicar():
            self._existente(eventId).update(copy.deepcopy(body))
            return copy.deepcopy(self.banco[eventId])

        return _Chamada(aplicar)

    def delete(self, calendarId, eventId):
        def apagar():
            self._existente(eventId)
            del self.banco[eventId]
            return ""

        return _Chamada(apagar)


class _Agendas:
    def get(self, calendarId):
        return _Chamada(lambda: {"id": "pessoa@exemplo.com", "summary": "pessoa@exemplo.com"})


class ServicoFalso:
    def __init__(self):
        self.banco: dict = {}
        self._eventos = _Eventos(self.banco)

    def events(self):
        return self._eventos

    def calendarList(self):
        return _Agendas()


@pytest.fixture
def servico(monkeypatch, tmp_path):
    falso = ServicoFalso()
    monkeypatch.setattr(calendario, "get_service", lambda escopos: falso)
    monkeypatch.setattr(criar, "get_service", lambda escopos: falso)
    monkeypatch.setattr(calendario, "ARQUIVO_CONSENTIMENTO", tmp_path / "consentimento.json")
    return falso


@pytest.fixture
def cliente(servico):
    app = FastAPI()
    app.include_router(calendario.router)
    return TestClient(app)


def _amanha(hora: int) -> str:
    dia = datetime.now(config.FUSO) + timedelta(days=1)
    return dia.replace(hour=hora, minute=0, second=0, microsecond=0).isoformat()


def test_ciclo_completo_criar_listar_editar_excluir(cliente, servico):
    resposta = cliente.post(
        "/calendar/events",
        json={"titulo": "Estudar", "inicio": _amanha(9), "fim": _amanha(10), "descricao": "Cap. 3", "local": "Casa", "meta": "Prova"},
    ).json()
    assert resposta["status"] == "sucesso"
    evento = resposta["dados"]["evento"]
    assert evento["titulo"] == "Estudar" and evento["local"] == "Casa" and evento["meta"] == "Prova"
    id_evento = evento["id"]
    assert servico.banco[id_evento]["extendedProperties"]["private"]["meta"] == "Prova"

    lista = cliente.get("/calendar/events").json()
    assert [e["id"] for e in lista["dados"]["eventos"]] == [id_evento]
    assert lista["dados"]["eventos"][0]["descricao"] == "Cap. 3"

    editado = cliente.put(
        f"/calendar/events/{id_evento}",
        json={"titulo": "Estudar mais", "inicio": _amanha(11), "fim": _amanha(12), "descricao": "", "local": "Biblioteca"},
    ).json()
    assert editado["status"] == "sucesso"
    assert editado["acao"] == "evento_editado"
    assert editado["dados"]["evento"]["titulo"] == "Estudar mais"
    assert editado["dados"]["evento"]["local"] == "Biblioteca"
    assert editado["dados"]["evento"]["inicio"] == _amanha(11)
    assert editado["dados"]["evento"]["meta"] == "Prova"

    obtido = cliente.get(f"/calendar/events/{id_evento}").json()
    assert obtido["dados"]["evento"]["titulo"] == "Estudar mais"

    excluido = cliente.request("DELETE", f"/calendar/events/{id_evento}", json={"evento_id": id_evento}).json()
    assert excluido["status"] == "sucesso"
    assert excluido["dados"]["evento_id"] == id_evento
    assert servico.banco == {}
    assert cliente.get(f"/calendar/events/{id_evento}").status_code == 404


def test_criar_no_passado_volta_erro_legivel(cliente):
    ontem = (datetime.now(config.FUSO) - timedelta(days=1)).replace(microsecond=0)
    resposta = cliente.post(
        "/calendar/events",
        json={"titulo": "X", "inicio": ontem.isoformat(), "fim": (ontem + timedelta(hours=1)).isoformat()},
    ).json()
    assert resposta["status"] == "erro"
    assert resposta["erro"]["mensagem"] == "Não é permitido criar eventos no passado."


def test_editar_com_fim_antes_do_inicio_falha_sem_chamar_o_google(cliente, servico):
    servico.banco["a"] = {"id": "a", "summary": "A", "start": {"dateTime": _amanha(9)}, "end": {"dateTime": _amanha(10)}}
    resposta = cliente.put(
        "/calendar/events/a", json={"titulo": "A", "inicio": _amanha(10), "fim": _amanha(9)}
    ).json()
    assert resposta["status"] == "erro"
    assert "anterior ao fim" in resposta["erro"]["mensagem"]
    assert servico.banco["a"]["start"]["dateTime"] == _amanha(9)


def test_excluir_inexistente(cliente):
    resposta = cliente.delete("/calendar/events/nada").json()
    assert resposta["status"] == "erro"
    assert resposta["erro"]["tipo"] == "nao_encontrado"


def test_evento_de_dia_inteiro_vira_iso_com_fuso(cliente, servico):
    servico.banco["f"] = {"id": "f", "summary": "Feriado", "start": {"date": "2026-12-25"}, "end": {"date": "2026-12-26"}}
    evento = cliente.get("/calendar/events").json()["dados"]["eventos"][0]
    assert evento["inicio"] == "2026-12-25T00:00:00-03:00"


def test_login_devolve_usuario_e_guarda_consentimento(cliente):
    resposta = cliente.post("/auth/google/session", json={"consent": {"termsAccepted": True}, "scopes": []})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["user"] == {"id": "pessoa@exemplo.com", "name": "pessoa", "email": "pessoa@exemplo.com"}
    assert calendario.ARQUIVO_CONSENTIMENTO.exists()
    assert cliente.post("/auth/logout").status_code == 204


def test_sem_credentials_responde_503(monkeypatch):
    def falhar(escopos):
        raise FileNotFoundError("Arquivo OAuth não encontrado")

    monkeypatch.setattr(calendario, "get_service", falhar)
    app = FastAPI()
    app.include_router(calendario.router)
    resposta = TestClient(app).get("/calendar/events")
    assert resposta.status_code == 503
    assert "OAuth" in resposta.json()["detail"]
