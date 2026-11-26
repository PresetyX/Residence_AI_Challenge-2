
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


def simular_eventos(eventos):
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {"ocupados": eventos},
    }
    return visualizador


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


def test_visualizar_eventos_marcados_pede_ocupados_e_omite_blocos_de_sono():
    evento = evento_teste()
    inicio = datetime.fromisoformat(evento["inicio"]).replace(hour=0)
    fim = inicio + timedelta(days=1)
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {
            "livres": [],
            "total_minutos_livres": 0,
            "ocupados": [
                {
                    "id": "e1",
                    "titulo": "Reunião",
                    "inicio": evento["inicio"],
                    "fim": evento["fim"],
                    "tipo": "evento",
                },
                {
                    "id": "sono",
                    "titulo": "Sono",
                    "inicio": inicio.isoformat(),
                    "fim": (inicio + timedelta(hours=8)).isoformat(),
                    "tipo": "sono",
                },
            ],
        },
    }
    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        consultar_llm=simular_llm(
            "visualizar",
            {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "tipo": "eventos"},
        ),
    )

    resposta = supervisor.executar("O que tenho agendado amanhã?")

    assert resposta["status"] == "sucesso"
    assert "Reunião" in resposta["mensagem"]
    assert "Sono" not in resposta["mensagem"]
    assert [evento["id"] for evento in resposta["dados"]["eventos"]] == ["e1"]
    visualizador.executar_json.assert_called_once_with(
        {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        incluir_ocupados=True,
    )


def test_visualizar_conflitos_mostra_intervalo_e_eventos_envolvidos():
    inicio = datetime.fromisoformat(evento_teste()["inicio"])
    fim = inicio + timedelta(hours=1)
    evento_a = {
        "id": "a",
        "titulo": "Reunião",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
        "tipo": "evento",
    }
    evento_b = {
        "id": "b",
        "titulo": "Aula",
        "inicio": fim.isoformat(),
        "fim": (fim + timedelta(hours=2)).isoformat(),
        "tipo": "evento",
    }
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {
            "ocupados": [evento_a, evento_b],
            "conflitos": [{
                "ids_eventos": ["a", "b"],
                "inicio_sobreposicao": fim.isoformat(),
                "fim_sobreposicao": (inicio + timedelta(hours=2)).isoformat(),
            }],
        },
    }
    periodo_inicio = inicio.replace(hour=0, minute=0)
    periodo_fim = periodo_inicio + timedelta(days=1)
    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        consultar_llm=simular_llm(
            "visualizar",
            {
                "inicio": periodo_inicio.isoformat(),
                "fim": periodo_fim.isoformat(),
                "tipo": "conflitos",
            },
        ),
    )

    resposta = supervisor.executar("Quais eventos estão em conflito amanhã?")

    assert resposta["status"] == "sucesso"
    assert "Reunião e Aula" in resposta["mensagem"]
    assert "das 11:00 às 12:00" in resposta["mensagem"]
    assert resposta["dados"]["conflitos"][0]["eventos"] == [evento_a, evento_b]
    visualizador.executar_json.assert_called_once_with(
        {"inicio": periodo_inicio.isoformat(), "fim": periodo_fim.isoformat()},
        incluir_ocupados=True,
        incluir_conflitos=True,
    )


def test_visualizar_conflitos_informa_quando_nao_ha_sobreposicoes():
    inicio = datetime.fromisoformat(evento_teste()["inicio"]).replace(hour=0, minute=0)
    fim = inicio + timedelta(days=1)
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {"ocupados": [], "conflitos": []},
    }
    supervisor = AgenteSupervisor(
        visualizador=visualizador,
        consultar_llm=simular_llm(
            "visualizar",
            {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "tipo": "conflitos"},
        ),
    )

    resposta = supervisor.executar("Tenho algum evento em conflito amanhã?")

    assert resposta["status"] == "sucesso"
    assert "Não encontrei eventos em conflito" in resposta["mensagem"]
    assert resposta["dados"] == {"conflitos": []}


def test_consulta_do_planejador_mantem_visualizacao_de_horarios_livres():
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {
        "status": "sucesso",
        "dados": {"livres": [], "total_minutos_livres": 0},
    }
    prazo = (datetime.now(config.FUSO).date() + timedelta(days=3)).isoformat()
    supervisor = AgenteSupervisor(visualizador=visualizador)

    resposta = supervisor.consultar_periodos_projeto(
        prazo,
        tarefas=[{"etapa": 1, "titulo": "Tarefa"}],
    )

    assert resposta["status"] == "sucesso"
    visualizador.executar_json.assert_called_once()
    assert visualizador.executar_json.call_args.kwargs == {}


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


def test_edicao_localiza_evento_e_so_edita_apos_confirmacao():
    evento = evento_teste()
    evento_agenda = {
        "id": "evt-1",
        "titulo": evento["titulo"],
        "inicio": evento["inicio"],
        "fim": evento["fim"],
        "tipo": "evento",
    }
    editor = MagicMock()
    editor.executar_json.return_value = {
        "status": "sucesso",
        "dados": {"evento": {**evento_agenda, "titulo": "Reunião atualizada"}},
    }
    dados = {
        "titulo_evento": "Reunião",
        "data_evento": evento["inicio"][:10],
        "alteracoes": {"titulo": "Reunião atualizada"},
    }
    supervisor = AgenteSupervisor(
        visualizador=simular_eventos([evento_agenda]),
        editor=editor,
        consultar_llm=simular_llm("editar", dados),
    )

    confirmacao = supervisor.executar("Mude a reunião de amanhã para Reunião atualizada")
    assert confirmacao["status"] == "confirmacao"
    editor.executar_json.assert_not_called()

    resposta = supervisor.executar("sim")
    assert resposta["status"] == "sucesso"
    assert resposta["acao"] == "editar"
    editor.executar_json.assert_called_once_with({"id": "evt-1", "titulo": "Reunião atualizada"})


def test_exclusao_cancela_sem_chamar_agente():
    evento = evento_teste()
    evento_agenda = {
        "id": "evt-2",
        "titulo": evento["titulo"],
        "inicio": evento["inicio"],
        "fim": evento["fim"],
        "tipo": "evento",
    }
    excluidor = MagicMock()
    supervisor = AgenteSupervisor(
        visualizador=simular_eventos([evento_agenda]),
        excluidor=excluidor,
        consultar_llm=simular_llm(
            "excluir",
            {"titulo_evento": "Reunião", "data_evento": evento["inicio"][:10]},
        ),
    )

    confirmacao = supervisor.executar("Exclua a reunião de amanhã")
    assert confirmacao["status"] == "confirmacao"
    resposta = supervisor.executar("não")
    assert resposta["status"] == "cancelado"
    excluidor.executar_json.assert_not_called()


def test_exclusao_chama_agente_apos_confirmacao():
    evento = evento_teste()
    evento_agenda = {
        "id": "evt-3",
        "titulo": evento["titulo"],
        "inicio": evento["inicio"],
        "fim": evento["fim"],
        "tipo": "evento",
    }
    excluidor = MagicMock()
    excluidor.executar_json.return_value = {"status": "sucesso"}
    supervisor = AgenteSupervisor(
        visualizador=simular_eventos([evento_agenda]),
        excluidor=excluidor,
        consultar_llm=simular_llm(
            "excluir",
            {"titulo_evento": "Reunião", "data_evento": evento["inicio"][:10]},
        ),
    )

    confirmacao = supervisor.executar("Exclua a reunião de amanhã")
    assert confirmacao["status"] == "confirmacao"
    resposta = supervisor.executar("sim")
    assert resposta["status"] == "sucesso"
    assert resposta["acao"] == "excluir"
    excluidor.executar_json.assert_called_once_with({"id": "evt-3"})


def test_eventos_ambiguos_pedem_horario_sem_escrever_na_agenda():
    evento = evento_teste()
    inicio_segundo = datetime.fromisoformat(evento["inicio"]) + timedelta(hours=2)
    fim_segundo = datetime.fromisoformat(evento["fim"]) + timedelta(hours=2)
    eventos = [
        {
            "id": "evt-1",
            "titulo": evento["titulo"],
            "inicio": evento["inicio"],
            "fim": evento["fim"],
            "tipo": "evento",
        },
        {
            "id": "evt-2",
            "titulo": evento["titulo"],
            "inicio": inicio_segundo.isoformat(),
            "fim": fim_segundo.isoformat(),
            "tipo": "evento",
        },
    ]
    excluidor = MagicMock()
    supervisor = AgenteSupervisor(
        visualizador=simular_eventos(eventos),
        excluidor=excluidor,
        consultar_llm=simular_llm(
            "excluir",
            {"titulo_evento": "Reunião", "data_evento": evento["inicio"][:10]},
        ),
    )

    resposta = supervisor.executar("Exclua a reunião de amanhã")
    assert resposta["status"] == "esclarecimento"
    assert "horário de início" in resposta["mensagem"]
    excluidor.executar_json.assert_not_called()


def test_horario_do_evento_desambigua_a_exclusao():
    evento = evento_teste()
    inicio_segundo = datetime.fromisoformat(evento["inicio"]) + timedelta(hours=2)
    fim_segundo = datetime.fromisoformat(evento["fim"]) + timedelta(hours=2)
    eventos = [
        {
            "id": "evt-1",
            "titulo": evento["titulo"],
            "inicio": evento["inicio"],
            "fim": evento["fim"],
            "tipo": "evento",
        },
        {
            "id": "evt-2",
            "titulo": evento["titulo"],
            "inicio": inicio_segundo.isoformat(),
            "fim": fim_segundo.isoformat(),
            "tipo": "evento",
        },
    ]
    excluidor = MagicMock()
    excluidor.executar_json.return_value = {"status": "sucesso"}
    supervisor = AgenteSupervisor(
        visualizador=simular_eventos(eventos),
        excluidor=excluidor,
        consultar_llm=simular_llm(
            "excluir",
            {
                "titulo_evento": "Reunião",
                "data_evento": evento["inicio"][:10],
                "hora_evento": inicio_segundo.strftime("%H:%M"),
            },
        ),
    )

    confirmacao = supervisor.executar("Exclua a reunião de amanhã das 12h")
    assert confirmacao["status"] == "confirmacao"
    resposta = supervisor.executar("sim")
    assert resposta["status"] == "sucesso"
    excluidor.executar_json.assert_called_once_with({"id": "evt-2"})


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


# ------------------------------- "sim"/"não" do cronograma não usa a LLM


def _supervisor_com_cronograma():
    llm = MagicMock()
    sup = AgenteSupervisor(visualizador=simular_visualizador(), criador=simular_criador(), consultar_llm=llm)
    sup.cronograma_pendente = [_dados(1, 8, 9)]
    return sup, llm


def test_cronograma_nao_cancela_sem_llm():
    sup, llm = _supervisor_com_cronograma()
    r = sup.executar("não")
    assert r["status"] == "cancelado" and sup.cronograma_pendente is None
    llm.assert_not_called()


def test_cronograma_resposta_estranha_pede_sim_ou_nao():
    sup, llm = _supervisor_com_cronograma()
    r = sup.executar("talvez")
    assert r["status"] == "confirmacao" and sup.cronograma_pendente is not None
    llm.assert_not_called()


def test_cronograma_sim_cria_sem_llm():
    sup, llm = _supervisor_com_cronograma()
    r = sup.executar("sim")
    assert r["acao"] == "planejar" and sup.cronograma_pendente is None
    llm.assert_not_called()
