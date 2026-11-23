"""POST /projetos lê o prazo do texto, e POST /prazos/interpretar lê uma resposta curta."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import backend.main as main
from destrava.core import config


class PlanejadorQueGuardaOPrazo:
    def __init__(self):
        self.prazos = []

    def executar(self, texto, prazo):
        self.prazos.append(prazo)
        return {"tarefas": [{"etapa": 1, "titulo": "Cadastro", "objetivo": "o", "entregaveis": "e",
                             "demonstracao": "d", "dependencia": 0, "story_points": 3}]}


class EstimadorFalso:
    def prever_lote(self, tarefas):
        return [5 for _ in tarefas]


def _cliente():
    planejador = PlanejadorQueGuardaOPrazo()
    main.app.state.planejador = planejador
    main.app.state.story_points_predictor = EstimadorFalso()
    return TestClient(main.app), planejador


def _hoje():
    return datetime.now(config.FUSO).date()


def test_prazo_no_proprio_texto():
    cliente, planejador = _cliente()
    resposta = cliente.post("/projetos", json={"texto": "Quero um app de receitas, tenho uma semana"}).json()
    esperado = (_hoje() + timedelta(weeks=1)).isoformat()
    assert resposta["prazo"] == esperado
    assert planejador.prazos == [esperado]
    assert "precisa_prazo" not in resposta


def test_prazo_explicito_tem_prioridade():
    cliente, planejador = _cliente()
    resposta = cliente.post("/projetos", json={"texto": "app até amanhã", "prazo": "2099-01-01"}).json()
    assert resposta["prazo"] == "2099-01-01"


def test_sem_prazo_planeja_e_pede_o_prazo():
    cliente, planejador = _cliente()
    resposta = cliente.post("/projetos", json={"texto": "Quero um app de receitas"}).json()
    assert resposta["prazo"] is None
    assert resposta["precisa_prazo"] is True
    assert len(resposta["tarefas"]) == 1
    assert planejador.prazos == [(_hoje() + timedelta(days=30)).isoformat()]


def test_prazo_que_ja_passou_da_422():
    cliente, _ = _cliente()
    resposta = cliente.post("/projetos", json={"texto": "app até 2020-01-01"})
    assert resposta.status_code == 422
    assert "já passou" in resposta.json()["detail"]


def test_interpretar_prazo():
    cliente, _ = _cliente()
    assert cliente.post("/prazos/interpretar", json={"texto": "até amanhã"}).json() == {
        "prazo": (_hoje() + timedelta(days=1)).isoformat()
    }
    assert cliente.post("/prazos/interpretar", json={"texto": "não sei"}).json() == {"prazo": None}
    assert cliente.post("/prazos/interpretar", json={"texto": "até 31/02"}).status_code == 422
