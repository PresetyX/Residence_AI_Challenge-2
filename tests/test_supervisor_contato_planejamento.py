"""Validacao do contrato atual: etapa e titulo, sem tempo da rede neural."""
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor


def test_recebe_etapa_e_titulo():
    planejador = MagicMock()
    planejador.executar.return_value = {"tarefas": [
        {"etapa": 0, "titulo": "Criar HTML"},
        {"etapa": 1, "titulo": "Estilizar CSS"},
    ]}
    resposta = AgenteSupervisor(planejador=planejador).receber_planejamento("Site", "2026-12-20")
    assert resposta["status"] == "sucesso"
    assert resposta["dados"]["tarefas"] == [
        {"etapa": 0, "titulo": "Criar HTML"},
        {"etapa": 1, "titulo": "Estilizar CSS"},
    ]


def test_rejeita_campos_antigos():
    planejador = MagicMock()
    planejador.executar.return_value = {"tarefas": [
        {"etapa": 0, "titulo": "Criar HTML", "dificuldade": 1}
    ]}
    resposta = AgenteSupervisor(planejador=planejador).receber_planejamento("Site", "2026-12-20")
    assert resposta["status"] == "erro"


def test_rejeita_titulo_vazio():
    planejador = MagicMock()
    planejador.executar.return_value = {"tarefas": [{"etapa": 0, "titulo": "  "}]}
    resposta = AgenteSupervisor(planejador=planejador).receber_planejamento("Site", "2026-12-20")
    assert resposta["status"] == "erro"


def test_planejador_sem_entender_vira_pedido_de_esclarecimento():
    from destrava.agents.planejador import MENSAGEM_NAO_ENTENDI, PedidoNaoEntendido

    planejador = MagicMock()
    planejador.executar.side_effect = PedidoNaoEntendido()
    resposta = AgenteSupervisor(planejador=planejador).receber_planejamento("asdf", "2026-12-20")
    assert resposta == {"status": "esclarecimento", "acao": "planejar", "mensagem": MENSAGEM_NAO_ENTENDI}
