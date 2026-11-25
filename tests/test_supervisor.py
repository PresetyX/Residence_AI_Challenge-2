
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


# ------------------------------------------------- LLM é a única interpretação


def _dados(dia_offset, h1, h2, data_texto=None):
    dia = datetime.now(config.FUSO).date() + timedelta(days=dia_offset)
    ini = data_texto or datetime.combine(dia, time(h1), tzinfo=config.FUSO).isoformat()
    fim = data_texto or datetime.combine(dia, time(h2), tzinfo=config.FUSO).isoformat()
    return {"titulo": "Futebol", "inicio": ini, "fim": fim}


def _supervisor(llm, visualizador=None, criador=None):
    chamadas = MagicMock(side_effect=llm)
    sup = AgenteSupervisor(
        visualizador=visualizador or simular_visualizador(),
        criador=criador or simular_criador(),
        consultar_llm=chamadas,
    )
    return sup, chamadas


def test_a_criar_valido_pede_confirmacao():
    sup, llm = _supervisor(simular_llm("criar", _dados(1, 17, 19)))
    r = sup.executar("Crie futebol amanhã das 5 da tarde até as 7 da noite")
    assert r["status"] == "confirmacao"
    assert "Responda 'sim' ou 'não'" in r["mensagem"]


def test_b_esclarecer_chama_a_llm():
    sup, llm = _supervisor(simular_llm("esclarecer", pergunta="Informe os horários."))
    r = sup.executar("Crie uma reunião amanhã")
    assert r["status"] == "esclarecimento"
    llm.assert_called_once()


def test_c_data_inexistente_da_llm():
    dados = _dados(1, 0, 0, data_texto="2027-02-31T14:00:00")
    sup, _ = _supervisor(simular_llm("criar", dados))
    r = sup.executar("Crie uma reunião em 31/02/2027 das 14h às 15h")
    assert r["status"] == "esclarecimento"
    assert "Dados inválidos" in r["mensagem"]


def test_d_criar_no_passado():
    sup, _ = _supervisor(simular_llm("criar", _dados(-1, 10, 11)))
    r = sup.executar("Crie uma reunião ontem das 10h às 11h")
    assert r["status"] == "esclarecimento"


def test_e_criar_durante_o_sono():
    sup, _ = _supervisor(simular_llm("criar", _dados(1, 2, 4)))
    r = sup.executar("Crie uma reunião amanhã das 2h às 4h")
    assert r["status"] == "erro"
    assert "sono" in r["mensagem"]


def test_f_criar_em_horario_ocupado():
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {
        "status": "sucesso", "dados": {"livres": [], "total_minutos_livres": 0}}
    sup, _ = _supervisor(simular_llm("criar", _dados(1, 17, 19)), visualizador=visualizador)
    r = sup.executar("Crie futebol amanhã das 17h às 19h")
    assert r["status"] == "erro"
    assert "livre" in r["mensagem"]


def test_g_confirmacao_sim_nao_e_outra_resposta():
    dados = _dados(1, 17, 19)
    criador = simular_criador()
    sup, _ = _supervisor(simular_llm("criar", dados), criador=criador)
    sup.executar("Crie futebol amanhã das 17h às 19h")
    assert "sim" in sup.executar("talvez")["mensagem"]
    assert sup.evento_pendente is not None
    assert sup.executar("sim")["status"] == "sucesso"
    criador.executar_json.assert_called_once()

    sup, _ = _supervisor(simular_llm("criar", dados), criador=criador)
    sup.executar("Crie futebol amanhã das 17h às 19h")
    assert sup.executar("não")["status"] == "cancelado"


def test_h_visualizar_continua_funcionando():
    dia = datetime.now(config.FUSO).date() + timedelta(days=1)
    dados = {"inicio": datetime.combine(dia, time.min, tzinfo=config.FUSO).isoformat(),
             "fim": datetime.combine(dia + timedelta(days=1), time.min, tzinfo=config.FUSO).isoformat()}
    sup, _ = _supervisor(simular_llm("visualizar", dados))
    r = sup.executar("Quais meus horários livres amanhã?")
    assert r["status"] == "sucesso" and r["acao"] == "visualizar"


def test_i_sem_validacao_por_regex_de_criacao():
    import inspect
    from destrava.agents import supervisor
    codigo = inspect.getsource(supervisor)
    for resto in ("crie|criar", "_horarios_do_pedido", "_conferir_texto"):
        assert resto not in codigo
    assert "quer_criar" not in codigo
