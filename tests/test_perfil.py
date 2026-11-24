from datetime import date, datetime, time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import perfil
from destrava.agents.supervisor import _horario_acordado
from destrava.core import config, pomodoro
from destrava.core.agenda_engine import gerar_blocos_sono
from destrava.core.encaixe_pomodoro import encaixar_tarefas_pomodoro, periodo_acordado
from destrava.core.horario import interpretar_duracao, interpretar_horario

EMAIL = "pessoa@exemplo.com"


@pytest.fixture
def cliente():
    app = FastAPI()
    app.include_router(perfil.router)
    return TestClient(app)


@pytest.mark.parametrize(
    "texto, tipo, esperado",
    [
        ("23h", "dormir", time(23)),
        ("23:30", "dormir", time(23, 30)),
        ("11 da noite", "dormir", time(23)),
        ("onze e meia", "dormir", time(23, 30)),
        ("23h e meia", "dormir", time(23, 30)),
        ("meia-noite", "dormir", time(0)),
        ("1 da manhã", "dormir", time(1)),
        ("lá pelas 2", "dormir", time(2)),
        ("10", "dormir", time(22)),
        ("7h", "acordar", time(7)),
        ("6:30", "acordar", time(6, 30)),
        ("sete e meia", "acordar", time(7, 30)),
        ("meio-dia", "acordar", time(12)),
        ("1 da tarde", "acordar", time(13)),
    ],
)
def test_interpretar_horario(texto, tipo, esperado):
    assert interpretar_horario(texto, tipo) == esperado


@pytest.mark.parametrize("texto", ["não sei", "cedo", "25h"])
def test_interpretar_horario_sem_hora_valida(texto):
    assert interpretar_horario(texto, "dormir") is None


@pytest.mark.parametrize(
    "texto, minutos",
    [
        ("2h", 120), ("1h30", 90), ("90 min", 90), ("meia hora", 30),
        ("uma hora e meia", 90), ("1 hora e 20", 80), ("2,5 horas", 150),
        ("1 dia", 480), ("3", 180), ("45", 45), ("1:15", 75), ("30m", 30),
    ],
)
def test_interpretar_duracao(texto, minutos):
    assert interpretar_duracao(texto) == minutos


def test_interpretar_duracao_sem_numero():
    assert interpretar_duracao("não faço ideia") is None


def test_perfil_novo_nao_tem_sono_nem_calibracao(cliente):
    corpo = cliente.get("/perfil", params={"email": EMAIL}).json()

    assert corpo["sono"] is None
    assert corpo["calibracao"] is None
    assert corpo["minutos_por_story_point"] == 60


def test_perfil_sem_conta_pede_login(cliente):
    assert cliente.get("/perfil").status_code == 401


def test_salvar_sono_grava_na_conta_e_aplica(cliente):
    perfil.ativar_conta(EMAIL)

    resposta = cliente.put("/perfil/sono", json={"email": EMAIL, "dormir": "23:30", "acordar": "7 da manhã"})

    assert resposta.status_code == 200
    assert resposta.json()["sono"] == {"dormir": "23:30", "acordar": "07:00"}
    assert config.HORARIO_DORMIR == time(23, 30)
    assert config.HORARIO_ACORDAR == time(7)
    # Continua salvo ao trocar de conta e voltar.
    perfil.ativar_conta("outra@exemplo.com")
    assert config.HORARIO_DORMIR == time(22)
    perfil.ativar_conta(EMAIL)
    assert config.HORARIO_ACORDAR == time(7)


@pytest.mark.parametrize(
    "dormir, acordar, trecho",
    [("abacaxi", "7h", "Não entendi o horário de dormir"), ("23h", "1h", "entre 3 e 14 horas")],
)
def test_salvar_sono_rejeita_entrada_invalida(cliente, dormir, acordar, trecho):
    resposta = cliente.put("/perfil/sono", json={"email": EMAIL, "dormir": dormir, "acordar": acordar})

    assert resposta.status_code == 422
    assert trecho in resposta.json()["detail"]


def test_interpretar_rota(cliente):
    assert cliente.post("/perfil/interpretar", json={"texto": "11 da noite", "tipo": "dormir"}).json() == {"valor": "23:00"}
    assert cliente.post("/perfil/interpretar", json={"texto": "1h30", "tipo": "duracao"}).json() == {"valor": 90}
    assert cliente.post("/perfil/interpretar", json={"texto": "sei lá", "tipo": "acordar"}).json() == {"valor": None}


def test_calibracao_fica_no_perfil_da_conta_ativa():
    perfil.ativar_conta(EMAIL)

    perfil.salvar_calibracao(42.4, [42, None])

    assert pomodoro.MINUTOS_POR_STORY_POINT == 42
    perfil.ativar_conta(None)
    assert pomodoro.MINUTOS_POR_STORY_POINT == 60
    perfil.ativar_conta(EMAIL)
    assert pomodoro.MINUTOS_POR_STORY_POINT == 42


def test_calibracao_descarta_resposta_fora_da_curva():
    # 30 min/SP em quase tudo; um "1000 minutos" para 1 SP não arrasta a média.
    media = perfil.calcular_minutos_por_story_point([90, 150, 1000, 60], [3, 5, 1, 2])

    assert media == pytest.approx(30)


def test_sono_depois_da_meia_noite(monkeypatch):
    monkeypatch.setattr(config, "HORARIO_DORMIR", time(1, 0))
    monkeypatch.setattr(config, "HORARIO_ACORDAR", time(9, 0))
    dia = date(2026, 11, 20)

    acordar, dormir = periodo_acordado(dia)
    assert (acordar.hour, dormir.day, dormir.hour) == (9, 21, 1)
    # 23h-0h30 ainda é acordado; 2h-3h é sono.
    assert _horario_acordado(datetime(2026, 11, 20, 23, tzinfo=config.FUSO), datetime(2026, 11, 21, 0, 30, tzinfo=config.FUSO))
    assert not _horario_acordado(datetime(2026, 11, 21, 2, tzinfo=config.FUSO), datetime(2026, 11, 21, 3, tzinfo=config.FUSO))
    blocos = gerar_blocos_sono(datetime(2026, 11, 20, 0, tzinfo=config.FUSO), datetime(2026, 11, 21, 0, tzinfo=config.FUSO))
    assert [(b.inicio.hour, b.fim.hour) for b in blocos] == [(1, 9)]


def test_encaixe_respeita_o_sono_do_perfil(monkeypatch):
    monkeypatch.setattr(config, "HORARIO_DORMIR", time(23, 0))
    monkeypatch.setattr(config, "HORARIO_ACORDAR", time(9, 0))
    agora = datetime(2026, 11, 20, 0, 0, tzinfo=config.FUSO)
    livres = [{"inicio": "2026-11-20T00:00:00-03:00", "fim": "2026-11-21T00:00:00-03:00"}]

    eventos, _ = encaixar_tarefas_pomodoro([{"titulo": "Tarefa", "story_points": 1}], livres, agora=agora)

    assert eventos[0]["inicio"].startswith("2026-11-20T09:00")
