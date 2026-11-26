"""Marcar etapas do plano como concluídas, com o tempo gasto (Google Calendar falso)."""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.calendario as calendario
import backend.main as main
from destrava.core import config
from tests.test_calendario_api import ServicoFalso


def _hora(h):
    dia = datetime.now(config.FUSO) + timedelta(days=1)
    return dia.replace(hour=h, minute=0, second=0, microsecond=0).isoformat()


def _evento(identificador, titulo, privado=None, descricao="passos"):
    evento = {"id": identificador, "summary": titulo, "description": descricao,
              "start": {"dateTime": _hora(9)}, "end": {"dateTime": _hora(10)}}
    if privado:
        evento["extendedProperties"] = {"private": privado}
    return evento


@pytest.fixture
def cenario(monkeypatch):
    servico = ServicoFalso()
    story_points = {}
    observacoes = []
    monkeypatch.setattr(calendario, "get_service", lambda escopos: servico)
    monkeypatch.setattr(calendario, "buscar_storypoints_evento", story_points.get)
    app = FastAPI()
    app.include_router(calendario.router)
    app.state.registrar_observacao = observacoes.append
    return TestClient(app), servico, story_points, observacoes


def _concluir(cliente, identificador="a", minutos=90):
    return cliente.post(f"/calendar/events/{identificador}/concluir", json={"tempo_gasto_minutos": minutos})


def test_conclui_com_o_tempo_sem_apagar_nem_alterar_o_evento(cenario):
    cliente, servico, *_ = cenario
    servico.banco["a"] = _evento("a", "[Destrava] Cadastrar gasto (Pomodoro)")
    antes = dict(servico.banco["a"])

    resposta = _concluir(cliente).json()

    assert resposta["status"] == "sucesso" and resposta["acao"] == "tarefa_concluida"
    evento = resposta["dados"]["evento"]
    assert evento["concluido"] is True and evento["tempo_gasto_minutos"] == 90
    depois = servico.banco["a"]
    assert {k: v for k, v in depois.items() if k != "extendedProperties"} == antes
    assert depois["extendedProperties"] == {"private": {"concluido": "true", "tempo_gasto_minutos": "90"}}
    listado = cliente.get("/calendar/events").json()["dados"]["eventos"][0]
    assert listado["tempo_gasto_minutos"] == 90


@pytest.mark.parametrize("corpo", [
    None, {}, {"tempo_gasto_minutos": 0}, {"tempo_gasto_minutos": -30}, {"tempo_gasto_minutos": 1441},
    {"tempo_gasto_minutos": "90"}, {"tempo_gasto_minutos": 1.5},
])
def test_sem_tempo_valido_nao_conclui(cenario, corpo):
    cliente, servico, _, observacoes = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")

    resposta = cliente.post("/calendar/events/a/concluir", json=corpo)

    assert resposta.status_code == 422
    assert "extendedProperties" not in servico.banco["a"] and observacoes == []


def test_tempo_entra_na_media_por_story_point(cenario):
    cliente, servico, story_points, observacoes = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")
    story_points["a"] = 3

    _concluir(cliente, minutos=90)

    assert observacoes == [30]


def test_parte_de_uma_etapa_conta_so_a_sua_fracao(cenario):
    cliente, servico, story_points, observacoes = cenario
    descricao = ("Etapa 1\nTrabalho estimado: 120 minutos.\n"
                 "Parte 1/2: 30 minutos de trabalho nesta parte.")
    servico.banco["a"] = _evento("a", "[Destrava] X - Parte 1/2 (Pomodoro)", descricao=descricao)
    story_points["a"] = 4  # da etapa inteira: esta parte vale 1 ponto

    _concluir(cliente, minutos=45)

    assert observacoes == [45]


def test_parte_sem_tamanho_conhecido_conclui_mas_nao_entra_na_media(cenario):
    cliente, servico, story_points, observacoes = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X - Parte 2/2")
    story_points["a"] = 4

    assert _concluir(cliente).json()["status"] == "sucesso"
    assert observacoes == []


def test_sem_story_points_conclui_mas_nao_entra_na_media(cenario):
    cliente, servico, _, observacoes = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")

    assert _concluir(cliente).json()["status"] == "sucesso"
    assert observacoes == []


def test_falha_no_historico_nao_desfaz_a_conclusao(cenario, monkeypatch):
    cliente, servico, *_ = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")

    def quebrar(_):
        raise OSError("disco")

    monkeypatch.setattr(calendario, "buscar_storypoints_evento", quebrar)

    assert _concluir(cliente).json()["status"] == "sucesso"


def test_nao_conclui_duas_vezes_nem_conta_o_tempo_em_dobro(cenario):
    cliente, servico, story_points, observacoes = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")
    story_points["a"] = 1
    _concluir(cliente, minutos=20)

    repetida = _concluir(cliente, minutos=200).json()

    assert repetida["status"] == "erro" and "já foi concluída" in repetida["erro"]["mensagem"]
    assert observacoes == [20]
    assert servico.banco["a"]["extendedProperties"]["private"]["tempo_gasto_minutos"] == "20"


def test_preserva_a_meta_do_plano(cenario):
    cliente, servico, *_ = cenario
    servico.banco["a"] = _evento("a", "Estudar", {"meta": "TCC"})

    evento = _concluir(cliente).json()["dados"]["evento"]

    assert evento["meta"] == "TCC" and evento["concluido"] is True


def test_compromisso_comum_nao_pode_ser_concluido(cenario):
    cliente, servico, *_ = cenario
    servico.banco["a"] = _evento("a", "Dentista")

    resposta = _concluir(cliente).json()

    assert resposta["status"] == "erro" and "etapas de um plano" in resposta["erro"]["mensagem"]
    assert "extendedProperties" not in servico.banco["a"]


def test_evento_inexistente_responde_404(cenario):
    cliente, *_ = cenario
    assert _concluir(cliente, "nada").status_code == 404


def test_evento_nao_concluido_nao_traz_as_marcas(cenario):
    cliente, servico, *_ = cenario
    servico.banco["a"] = _evento("a", "[Destrava] X")
    evento = cliente.get("/calendar/events/a").json()["dados"]["evento"]
    assert "concluido" not in evento and "tempo_gasto_minutos" not in evento


def test_o_backend_liga_a_conclusao_a_media_do_historico(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "CAMINHO_HISTORICO", tmp_path / "historico.json")
    monkeypatch.setattr(main, "media_minutos_por_story_point", 30.0)
    monkeypatch.setattr(main, "_quantidade_observacoes_media", 1)

    main.app.state.registrar_observacao(60.0)

    assert main.media_minutos_por_story_point == 45.0
