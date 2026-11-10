"""Testes da conferência de datas/horários do Supervisor, sem Google ou Ollama.

Copie para tests/test_supervisor_validacoes.py e execute:
    python -m pytest -q tests/test_supervisor_validacoes.py
"""
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


def _amanha():
    return (datetime.now(config.FUSO) + timedelta(days=1)).date()


def _data_hora(data, horas):
    return datetime.fromisoformat(f"{data.isoformat()}T{horas}:00").replace(
        tzinfo=config.FUSO
    ).isoformat()


def _supervisor_simulado(respostas):
    visualizador = MagicMock()
    criador = MagicMock()
    amanha = _amanha()
    visualizador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {
            "livres": [{
                "inicio": _data_hora(amanha, "00:00"),
                "fim": _data_hora(amanha, "23:59"),
            }],
            "total_minutos_livres": 1439,
        },
    }
    criador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {"evento": {
            "titulo": "Reunião",
            "inicio": _data_hora(amanha, "13:00"),
            "fim": _data_hora(amanha, "14:00"),
        }},
    }
    iterador = iter(respostas)
    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        criador=criador,
        consultar_llm=lambda _: json.dumps(next(iterador)),
    )
    return supervisor, visualizador, criador


def _criar(data, inicio, fim):
    return {"acao": "criar", "dados": {
        "titulo": "Reunião",
        "inicio": _data_hora(data, inicio),
        "fim": _data_hora(data, fim),
    }}


def test_data_31_de_fevereiro_e_rejeitada():
    supervisor, visualizador, criador = _supervisor_simulado([])
    resposta = supervisor.executar(
        "Crie um evento em 31/02/2027 das 10h às 11h."
    )
    assert "31/02/2027" in resposta["mensagem"]
    assert resposta["status"] == "esclarecimento"
    visualizador.executar_json.assert_not_called()
    criador.executar_json.assert_not_called()


def test_gemma_nao_pode_trocar_1h_as_3h_por_9h_as_11h():
    supervisor, visualizador, criador = _supervisor_simulado([
        _criar(_amanha(), "09:00", "11:00")
    ])
    resposta = supervisor.executar(
        "Crie uma reunião amanhã das 1 às 3 da manhã."
    )
    assert "01:00 às 03:00" in resposta["mensagem"]
    assert "09:00 às 11:00" in resposta["mensagem"]
    visualizador.executar_json.assert_not_called()
    criador.executar_json.assert_not_called()


def test_gemma_nao_pode_inventar_horarios_ausentes():
    supervisor, visualizador, criador = _supervisor_simulado([
        _criar(_amanha(), "09:00", "11:00")
    ])
    resposta = supervisor.executar("Crie uma reunião amanhã.")
    assert resposta["status"] == "esclarecimento"
    assert "horários" in resposta["mensagem"]
    assert supervisor.pedido_em_esclarecimento is not None
    visualizador.executar_json.assert_not_called()
    criador.executar_json.assert_not_called()


def test_data_nao_pode_ser_trocada_pela_gemma():
    amanha = _amanha()
    supervisor, visualizador, criador = _supervisor_simulado([
        _criar(amanha + timedelta(days=1), "13:00", "14:00")
    ])
    resposta = supervisor.executar(
        f"Crie uma reunião no dia {amanha:%d/%m/%Y} das 13h às 14h."
    )
    assert "A IA interpretou a data" in resposta["mensagem"]
    visualizador.executar_json.assert_not_called()
    criador.executar_json.assert_not_called()


def test_esclarecimento_criacao_e_confirmacao():
    supervisor, visualizador, criador = _supervisor_simulado([
        {"acao": "esclarecer", "pergunta": "Qual o horário da reunião?"},
        _criar(_amanha(), "13:00", "14:00"),
    ])
    primeiro = supervisor.executar("Crie uma reunião amanhã.")
    segundo = supervisor.executar("Das 13h às 14h.")
    terceiro = supervisor.executar("sim")
    assert primeiro["status"] == "esclarecimento"
    assert segundo["status"] == "confirmacao"
    assert terceiro["status"] == "sucesso"
    criador.executar_json.assert_called_once()
