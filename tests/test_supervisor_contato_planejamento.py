"""Validacao do contrato atual: etapa e titulo, sem tempo da rede neural."""
from destrava.agents.supervisor import AgenteSupervisor


def test_recebe_etapa_e_titulo():
    tarefas = [
        {"etapa": 0, "titulo": "Criar HTML"},
        {"etapa": 1, "titulo": "Estilizar CSS"},
    ]
    resposta = AgenteSupervisor().receber_planejamento("2026-12-20", tarefas)
    assert resposta["status"] == "sucesso"
    assert resposta["dados"]["tarefas"] == [
        {"etapa": 0, "titulo": "Criar HTML"},
        {"etapa": 1, "titulo": "Estilizar CSS"},
    ]


def test_rejeita_campos_antigos():
    tarefas = [
        {"etapa": 0, "titulo": "Criar HTML", "dificuldade": 1}
    ]
    resposta = AgenteSupervisor().receber_planejamento("2026-12-20", tarefas)
    assert resposta["status"] == "erro"


def test_rejeita_titulo_vazio():
    tarefas = [{"etapa": 0, "titulo": "  "}]
    resposta = AgenteSupervisor().receber_planejamento("2026-12-20", tarefas)
    assert resposta["status"] == "erro"


def test_lista_de_tarefas_e_obrigatoria():
    resposta = AgenteSupervisor().receber_planejamento("2026-12-20")
    assert resposta["status"] == "erro"
