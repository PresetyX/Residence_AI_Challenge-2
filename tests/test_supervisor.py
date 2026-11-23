
"""Testes do Supervisor do Destrava.

Os testes utilizam simulações (mocks).
Não acessam o Google Calendar nem executam o Ollama.
"""

import json
from datetime import datetime, timedelta, time
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


# Gera um evento de teste para amanhã.
def evento_teste():
    amanha = datetime.now(config.FUSO).date() + timedelta(days=1)

    inicio = datetime.combine(
        amanha, time(10, 0), tzinfo=config.FUSO
    )

    fim = datetime.combine(
        amanha, time(11, 0), tzinfo=config.FUSO
    )

    return {
        "titulo": "Reunião",
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat()
    }


# Simula a interpretação da LLM.
def simular_llm(acao, dados=None, pergunta=None):
    resposta = {
        "acao": acao,
        "dados": dados,
        "pergunta": pergunta
    }

    return lambda prompt: json.dumps(resposta)


# Simula o Agente Visualizar com horário livre.
def simular_visualizador():
    visualizador = MagicMock()

    def consultar(dados):
        return {
            "status": "sucesso",
            "dados": {
                "livres": [
                    {
                        "inicio": dados["inicio"],
                        "fim": dados["fim"],
                        "duracao_minutos": 60
                    }
                ],
                "total_minutos_livres": 60
            }
        }

    visualizador.executar_json.side_effect = consultar

    return visualizador


# Simula o Agente Criar com sucesso.
def simular_criador():
    criador = MagicMock()

    def criar(dados):
        return {
            "status": "sucesso",
            "dados": {
                "evento": {
                    "id": "123",
                    "titulo": dados["titulo"],
                    "inicio": dados["inicio"],
                    "fim": dados["fim"]
                }
            }
        }

    criador.executar_json.side_effect = criar

    return criador


# TESTE 1 - Verifica a consulta da agenda.
def test_visualizar_encaminha_json_ao_agente():
    evento = evento_teste()
    visualizador = simular_visualizador()

    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        consultar_llm=simular_llm(
            "visualizar",
            {
                "inicio": evento["inicio"],
                "fim": evento["fim"]
            }
        )
    )

    resposta = supervisor.executar(
        "Quais horários tenho livres amanhã?"
    )

    assert resposta["status"] == "sucesso"
    assert resposta["acao"] == "visualizar"

    visualizador.executar_json.assert_called_once()


# TESTE 2 - Verifica pedidos sem informações suficientes.
def test_pedido_ambiguo_nao_consulta_google():
    visualizador = MagicMock()

    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        consultar_llm=simular_llm(
            "esclarecer",
            pergunta="Para qual dia deseja consultar a agenda?"
        )
    )

    resposta = supervisor.executar("Estou livre?")

    assert resposta["status"] == "esclarecimento"

    visualizador.executar_json.assert_not_called()


# TESTE 3 - Verifica criação com informações incompletas.
def test_criacao_incompleta_pede_esclarecimento():
    visualizador = MagicMock()
    criador = MagicMock()

    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        criador=criador,
        consultar_llm=simular_llm(
            "criar",
            dados=None
        )
    )

    resposta = supervisor.executar(
        "Cria uma reunião amanhã"
    )

    assert resposta["status"] == "esclarecimento"

    criador.executar_json.assert_not_called()


# TESTE 4 - Verifica se o Supervisor pede confirmação.
def test_criacao_pede_confirmacao():
    evento = evento_teste()
    criador = simular_criador()

    supervisor = AgenteSupervisor(
        visualizador=simular_visualizador(),
        criador=criador,
        consultar_llm=simular_llm("criar", evento)
    )

    resposta = supervisor.executar(
        "Crie uma reunião amanhã das 10h às 11h"
    )

    assert resposta["status"] == "confirmacao"
    assert supervisor.evento_pendente is not None

    # Ainda não pode criar o evento.
    criador.executar_json.assert_not_called()


# TESTE 5 - Verifica a confirmação com "sim".
def test_confirmacao_sim_cria_evento():
    evento = evento_teste()
    criador = simular_criador()

    supervisor = AgenteSupervisor(
        visualizador=simular_visualizador(),
        criador=criador,
        consultar_llm=simular_llm("criar", evento)
    )

    supervisor.executar(
        "Crie uma reunião amanhã das 10h às 11h"
    )

    resposta = supervisor.executar("sim")

    assert resposta["status"] == "sucesso"
    assert resposta["acao"] == "criar"

    criador.executar_json.assert_called_once_with(evento)

    assert supervisor.evento_pendente is None


# TESTE 6 - Verifica o cancelamento com "não".
def test_confirmacao_nao_cancela():
    evento = evento_teste()
    criador = simular_criador()

    supervisor = AgenteSupervisor(
        visualizador=simular_visualizador(),
        criador=criador,
        consultar_llm=simular_llm("criar", evento)
    )

    supervisor.executar(
        "Crie uma reunião amanhã das 10h às 11h"
    )

    resposta = supervisor.executar("não")

    assert resposta["status"] == "cancelado"
    assert supervisor.evento_pendente is None

    criador.executar_json.assert_not_called()


# TESTE 7 - Impede criação em horário ocupado.
def test_horario_ocupado_nao_cria():
    evento = evento_teste()

    visualizador = MagicMock()
    visualizador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {
            "livres": [],
            "total_minutos_livres": 0
        }
    }

    criador = simular_criador()

    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        criador=criador,
        consultar_llm=simular_llm("criar", evento)
    )

    resposta = supervisor.executar(
        "Crie uma reunião amanhã das 10h às 11h"
    )

    assert resposta["status"] == "erro"
    assert supervisor.evento_pendente is None

    criador.executar_json.assert_not_called()


# TESTE 8 - Verifica JSON inválido da LLM.
def test_json_invalido_nao_consulta_google():
    visualizador = MagicMock()

    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        consultar_llm=lambda prompt: "JSON inválido"
    )

    resposta = supervisor.executar(
        "Quais horários tenho livres amanhã?"
    )

    assert resposta["status"] == "erro"

    visualizador.executar_json.assert_not_called()


# TESTE 9 - Verifica datas inválidas.
def test_datas_invalidas_nao_consultam_google():
    visualizador = MagicMock()

    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        consultar_llm=simular_llm(
            "visualizar",
            {
                "inicio": "data_invalida",
                "fim": "outra_data_invalida"
            }
        )
    )

    resposta = supervisor.executar(
        "Quais horários tenho livres?"
    )

    assert resposta["status"] == "esclarecimento"

    visualizador.executar_json.assert_not_called()
