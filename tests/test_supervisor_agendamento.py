"""Testa a Etapa 3 sem acessar Google Calendar nem executar Ollama.

Execute: python -m pytest tests/test_supervisor_agendamento.py -v
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


def montar_supervisor(tarefas=3):
    inicio = datetime.now(config.FUSO).replace(hour=19, minute=0, second=0, microsecond=0) + timedelta(days=1)
    fim = inicio + timedelta(hours=4)

    agente_criar = MagicMock()
    agente_criar.executar_json.side_effect = lambda evento: {
        "status": "sucesso",
        "dados": {"evento": {"id": evento["titulo"], **evento}},
        "fluxo": {"fim": {"detalhe": {"periodo_confere": True}}},
    }
    supervisor = AgenteSupervisor(
        visualizador=MagicMock(),
        criador=agente_criar,
        planejador=MagicMock(),
    )
    supervisor.consultar_periodos_projeto = MagicMock(return_value={
        "status": "sucesso",
        "dados": {
            "tarefas": [
                {"ordem": i, "titulo": f"Tarefa {i}", "tipo": "frontend", "dificuldade": 1}
                for i in range(1, tarefas + 1)
            ],
            "livres": [{"inicio": inicio.isoformat(), "fim": fim.isoformat()}],
        },
    })
    supervisor.verificar_disponibilidade = MagicMock(return_value=True)
    return supervisor, agente_criar


def test_previa_nao_cria_eventos():
    supervisor, criador = montar_supervisor()
    resposta = supervisor.preparar_agendamento("Site", "2026-11-20")
    assert resposta["status"] == "confirmacao"
    assert len(resposta["dados"]["eventos"]) == 3
    assert all(evento["titulo"].startswith("[Destrava]") for evento in resposta["dados"]["eventos"])
    criador.executar_json.assert_not_called()


def test_sim_cria_uma_unica_vez():
    supervisor, criador = montar_supervisor()
    supervisor.preparar_agendamento("Site", "2026-11-20")
    resposta = supervisor.confirmar_agendamento(True)
    assert resposta["status"] == "sucesso"
    assert criador.executar_json.call_count == 3
    assert supervisor.confirmar_agendamento(True)["status"] == "erro"
    assert criador.executar_json.call_count == 3


def test_nao_cancela_sem_criar():
    supervisor, criador = montar_supervisor()
    supervisor.preparar_agendamento("Site", "2026-11-20")
    assert supervisor.confirmar_agendamento(False)["status"] == "cancelado"
    criador.executar_json.assert_not_called()


def test_conflito_bloqueia_todo_agendamento():
    supervisor, criador = montar_supervisor()
    supervisor.preparar_agendamento("Site", "2026-11-20")
    supervisor.verificar_disponibilidade.return_value = False
    assert supervisor.confirmar_agendamento(True)["status"] == "erro"
    criador.executar_json.assert_not_called()


def test_sem_espaco_nao_cria():
    supervisor, criador = montar_supervisor(tarefas=5)
    assert supervisor.preparar_agendamento("Site", "2026-11-20")["status"] == "erro"
    criador.executar_json.assert_not_called()


def test_erro_apos_um_evento_informa_criacao_parcial():
    supervisor, criador = montar_supervisor()
    chamado = 0

    def criar(evento):
        nonlocal chamado
        chamado += 1
        if chamado == 2:
            return {"status": "erro", "erro": {"mensagem": "Falha simulada"}}
        return {"status": "sucesso", "dados": {"evento": {"id": "1", **evento}}}

    criador.executar_json.side_effect = criar
    supervisor.preparar_agendamento("Site", "2026-11-20")
    resposta = supervisor.confirmar_agendamento(True)
    assert resposta["status"] == "parcial"
    assert len(resposta["dados"]["eventos_criados"]) == 1
