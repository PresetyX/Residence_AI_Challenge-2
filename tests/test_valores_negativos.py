"""Horários, durações e prazos negativos são recusados (sem Google, Ollama ou rede)."""

from datetime import datetime, time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config
from destrava.core.horario import interpretar_duracao, interpretar_horario, tem_numero_negativo
from destrava.core.prazo import interpretar_prazo

QUARTA = datetime(2026, 11, 25, 12, 0, tzinfo=config.FUSO)


@pytest.mark.parametrize("texto", ["-1h", "-23h", "-7:30", "menos 2 horas", "-30h", "às -3h", "−1h"])
def test_sono_negativo_e_recusado(texto):
    assert interpretar_horario(texto, "dormir") is None
    assert interpretar_horario(texto, "acordar") is None


@pytest.mark.parametrize("texto", ["-2h", "-45 min", "-3", "-1h30", "-2,5 horas", "menos 3 horas", "-1 dia"])
def test_duracao_negativa_e_recusada(texto):
    assert interpretar_duracao(texto) is None


@pytest.mark.parametrize("texto, minutos", [
    ("2h", 120), ("45 min", 45), ("1h30", 90), ("mais ou menos 2h", 120), ("pelo menos 3 horas", 180),
])
def test_duracao_normal_continua_valendo(texto, minutos):
    assert interpretar_duracao(texto) == minutos


@pytest.mark.parametrize("texto, esperado", [("23h", time(23)), ("1h30", time(1, 30)), ("11 da noite", time(23))])
def test_sono_normal_continua_valendo(texto, esperado):
    assert interpretar_horario(texto, "dormir") == esperado


@pytest.mark.parametrize("texto", [
    "app em -3 dias", "tenho -2 semanas", "entrega em -1 mês", "prazo de -10 dias",
    "reunião das -1h às 2h", "reunião das 10h às -11h", "amanhã às -3h",
])
def test_reconhece_negativos_em_frases(texto):
    assert tem_numero_negativo(texto)


@pytest.mark.parametrize("texto", [
    "reunião 13h-14h", "reunião das 10h - 11h", "das 10h -11h", "entrega 20-12", "até 2026-12-20",
    "2026-12-20T10:00:00-03:00", "sexta-feira às 10h", "reunião da turma -2 amanhã",
    "pelo menos 2 dias", "app em 3 dias",
])
def test_traco_comum_nao_e_numero_negativo(texto):
    assert not tem_numero_negativo(texto)


def test_prazo_negativo_da_erro_e_prazo_normal_continua():
    with pytest.raises(ValueError, match="negativo"):
        interpretar_prazo("app em -3 dias", QUARTA)
    assert interpretar_prazo("app em 3 dias", QUARTA).isoformat() == "2026-11-28"


@pytest.mark.parametrize("pedido", [
    "Crie uma reunião amanhã das -1h às 2h", "Marque estudo amanhã às -3h por 1 hora",
])
def test_chat_recusa_sem_chamar_a_llm(pedido):
    llm, criador = MagicMock(), MagicMock()
    resposta = AgenteSupervisor(visualizador=MagicMock(), criador=criador, consultar_llm=llm).executar(pedido)
    assert resposta["status"] == "esclarecimento" and "negativos" in resposta["mensagem"]
    llm.assert_not_called()
    criador.executar_json.assert_not_called()


def test_api_de_prazo_responde_422_com_a_explicacao():
    resposta = TestClient(main.app).post("/prazos/interpretar", json={"texto": "em -3 dias"})
    assert resposta.status_code == 422
    assert "negativo" in resposta.json()["detail"]
