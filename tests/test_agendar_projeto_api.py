"""Rotas /projetos/agendar e /projetos/agendar/confirmar (Supervisor com agentes falsos)."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.chat as chat
import backend.main as main
from backend.database import buscar_storypoints_evento
from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config

TAREFAS = [
    {"etapa": 1, "titulo": "Login", "objetivo": "x", "entregaveis": "y", "demonstracao": "z", "dependencia": 0, "story_points": 5},
    {"etapa": 2, "titulo": "Cadastro", "objetivo": "x", "entregaveis": "y", "demonstracao": "z", "dependencia": 1, "story_points": 3},
]


class VisualizadorFalso:
    def __init__(self, livres):
        self.livres = livres

    def executar_json(self, pedido):
        return {"status": "sucesso", "dados": {"livres": self.livres, "total_minutos_livres": 0}}


class CriadorFalso:
    def __init__(self):
        self.criados = []

    def executar_json(self, evento):
        criado = {"id": f"e{len(self.criados) + 1}", **evento}
        self.criados.append(criado)
        return {"status": "sucesso", "dados": {"evento": criado}}


def _cliente(livres):
    app = FastAPI()
    app.include_router(chat.router)
    criador = CriadorFalso()
    supervisor = AgenteSupervisor(visualizador=VisualizadorFalso(livres), criador=criador)
    supervisor.verificar_disponibilidade = lambda evento: True
    app.state.supervisor = supervisor
    app.post("/projetos/agendar")(main.agendar_projeto)
    app.post("/projetos/agendar/confirmar")(main.confirmar_agendamento)
    return TestClient(app), criador


def _amanha(hora):
    dia = datetime.now(config.FUSO) + timedelta(days=1)
    return dia.replace(hour=hora, minute=0, second=0, microsecond=0).isoformat()


def _prazo():
    return (datetime.now(config.FUSO) + timedelta(days=3)).date().isoformat()


def test_prevê_classifica_e_cria():
    cliente, criador = _cliente([{"inicio": _amanha(8), "fim": _amanha(18), "duracao_minutos": 600}])
    previa = cliente.post(
        "/projetos/agendar",
        json={"prazo": _prazo(), "tarefas": TAREFAS},
    ).json()
    assert previa["status"] == "confirmacao"
    assert previa["classificacao"] in ("tranquilo", "corrido")
    assert len(previa["dados"]["eventos"]) == 2
    assert criador.criados == []  # nada é criado antes do "sim"

    resultado = cliente.post("/projetos/agendar/confirmar", json={"confirmado": True}).json()
    assert resultado["status"] == "sucesso"
    assert len(criador.criados) == 2
    assert all(buscar_storypoints_evento(evento["id"]) == 0 for evento in criador.criados)

    # Outro "sim" não repete a criação.
    de_novo = cliente.post("/projetos/agendar/confirmar", json={"confirmado": True}).json()
    assert de_novo["status"] == "erro"
    assert len(criador.criados) == 2


def test_sem_horario_livre_o_prazo_e_impossivel():
    cliente, criador = _cliente([])
    previa = cliente.post(
        "/projetos/agendar", json={"prazo": _prazo(), "tarefas": TAREFAS}
    ).json()
    assert previa["status"] == "erro"
    assert previa["classificacao"] == "impossivel"
    assert criador.criados == []


def test_cancelar_nao_cria_nada():
    cliente, criador = _cliente([{"inicio": _amanha(8), "fim": _amanha(18), "duracao_minutos": 600}])
    cliente.post("/projetos/agendar", json={"prazo": _prazo(), "tarefas": TAREFAS})
    resultado = cliente.post("/projetos/agendar/confirmar", json={"confirmado": False}).json()
    assert resultado["status"] == "cancelado"
    assert criador.criados == []
