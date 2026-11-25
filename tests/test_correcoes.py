"""Regressões dos defeitos da validação dos agentes (sem Google, Ollama ou rede)."""

import json
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock

import pytest

from destrava.agents import planejador as modulo_planejador
from destrava.tools import visualizar as modulo_visualizar
from destrava.tools.editar import AgenteEditar
from destrava.agents.planejador import (
    AgentePlanejador,
    PedidoNaoEntendido,
    fundir_configuracao,
    problemas_do_plano,
)
from destrava.agents.supervisor import AgenteSupervisor, _data_do_pedido, _horarios_do_pedido
from destrava.tools.visualizar import AgenteVisualizar
from destrava.core import config
from destrava.core.intencao import classificar_confirmacao, consulta_agenda, pede_projeto

# Quarta-feira fixa para as regras de data.
QUARTA = datetime(2026, 11, 25, 12, 0, tzinfo=config.FUSO)


def _hora(dias, h, m=0):
    dia = datetime.now(config.FUSO).date() + timedelta(days=dias)
    return datetime.combine(dia, time(h, m), tzinfo=config.FUSO)


# ---------------------------------------------------------------- confirmação


@pytest.mark.parametrize("texto", ["sim", "Sim.", "sim!", "s", "Sim, pode criar", "ok", "pode agendar", "confirmo"])
def test_sim_claro(texto):
    assert classificar_confirmacao(texto) is True


@pytest.mark.parametrize("texto", [
    "não", "não.", "n", "cancela", "pode cancelar", "quero cancelar", "ok, cancela", "isso não",
    "agenda não", "não, muda para as 18h",
])
def test_nao_ou_cancelamento_nunca_vira_sim(texto):
    assert classificar_confirmacao(texto) is False


@pytest.mark.parametrize("texto", [
    "vai cancelar?", "sim, mas muda o horário", "quero ver minha agenda", "talvez", "pode?",
    "quero um app de gastos",
])
def test_duvida_nao_confirma(texto):
    assert classificar_confirmacao(texto) is not True


# ---------------------------------------------------------------- projeto x agenda


@pytest.mark.parametrize("texto", [
    "Quero criar um app de agenda para barbearia",
    "Quero desenvolver um sistema de reserva de horários",
    "Preciso criar um site para marcar consulta médica",
    "Preciso planejar um projeto de app de receitas até 20/12",
    "Me ajude a dividir meu TCC em tarefas",
    "Programa de terminal em Python para tarefas",
])
def test_reconhece_pedido_de_projeto(texto):
    assert pede_projeto(texto)
    llm = MagicMock()
    resposta = AgenteSupervisor(visualizador=MagicMock(), criador=MagicMock(), consultar_llm=llm).executar(texto)
    assert (resposta["status"], resposta["acao"]) == ("indisponivel", "planejar")
    llm.assert_not_called()


@pytest.mark.parametrize("texto", [
    "Crie uma reunião sobre o app amanhã das 10h às 11h",
    "Quais meus horários livres para fazer o projeto?",
    "O projeto atrasou, quais meus horários livres?",
    "Programa uma reunião amanhã",
    "Marque estudo de cálculo amanhã das 9h às 10h",
])
def test_agenda_nao_vira_projeto(texto):
    assert not pede_projeto(texto)


@pytest.mark.parametrize("texto", [
    "Quero ver meus horários livres amanhã para marcar dentista",
    "Tenho tempo amanhã para agendar uma consulta?",
])
def test_consulta_com_verbo_de_marcar_chega_ao_visualizar(texto):
    assert consulta_agenda(texto)
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {"status": "sucesso", "dados": {"livres": [], "total_minutos_livres": 0}}
    llm = lambda prompt: json.dumps({"acao": "visualizar", "dados": {
        "inicio": _hora(1, 0).isoformat(), "fim": _hora(2, 0).isoformat()}})
    resposta = AgenteSupervisor(visualizador=visualizador, criador=MagicMock(), consultar_llm=llm).executar(texto)
    assert resposta["acao"] == "visualizar" and resposta["status"] == "sucesso"


# ---------------------------------------------------------------- datas e horários


@pytest.mark.parametrize("texto, esperado", [
    ("reunião na sexta", "2026-11-27"),
    ("reunião sexta-feira", "2026-11-27"),
    ("reunião na próxima quarta", "2026-12-02"),
    ("reunião 27/11", "2026-11-27"),
    ("reunião dia 3/1", "2027-01-03"),
])
def test_dia_da_semana_e_data_sem_ano(texto, esperado):
    data, erro = _data_do_pedido(texto, QUARTA)
    assert erro is None and data.isoformat() == esperado


@pytest.mark.parametrize("texto", [
    "na quarta",                       # o próprio dia: ambíguo
    "livre de segunda a sexta",        # intervalo
    "a sexta reunião do grupo",        # ordinal
    "estudar 1/2 hora",
])
def test_textos_sem_data_definida(texto):
    assert _data_do_pedido(texto, QUARTA) == (None, None)


def test_data_sem_ano_inexistente():
    assert "não existe" in _data_do_pedido("dia 31/02", QUARTA)[1]


@pytest.mark.parametrize("texto, esperado", [
    ("das 11h às 1 da tarde", (time(11), time(13))),
    ("das 2 às 3 da tarde", (time(14), time(15))),
    ("das 9h às 1 da tarde", (time(9), time(13))),
])
def test_periodo_da_tarde(texto, esperado):
    assert _horarios_do_pedido(texto) == (esperado, None)


def test_consulta_com_data_errada_da_llm_e_corrigida():
    visualizador = MagicMock()
    visualizador.executar_json.return_value = {"status": "sucesso", "dados": {"livres": [], "total_minutos_livres": 0}}
    llm = lambda prompt: json.dumps({"acao": "visualizar", "dados": {
        "inicio": _hora(9, 0).isoformat(), "fim": _hora(10, 0).isoformat()}})
    AgenteSupervisor(visualizador=visualizador, criador=MagicMock(), consultar_llm=llm).executar(
        "Quais meus horários livres amanhã?")
    pedido = visualizador.executar_json.call_args.args[0]
    assert pedido["inicio"][:10] == _hora(1, 0).date().isoformat()
    assert pedido["fim"][:10] == _hora(2, 0).date().isoformat()


def test_prompt_informa_o_dia_da_semana():
    prompts = []

    def llm(prompt):
        prompts.append(prompt)
        return json.dumps({"acao": "fora_escopo"})

    AgenteSupervisor(visualizador=MagicMock(), criador=MagicMock(), consultar_llm=llm).executar("oi")
    assert "Próximos dias:" in prompts[0] and "sexta-feira = " in prompts[0]


def test_pedido_de_esclarecimento_nao_repete_a_frase():
    llm = lambda prompt: json.dumps({"acao": "esclarecer", "pergunta": "Qual o título? Envie um novo pedido completo."})
    resposta = AgenteSupervisor(visualizador=MagicMock(), criador=MagicMock(), consultar_llm=llm).executar("oi")
    assert resposta["mensagem"].count("novo pedido") == 1


# ---------------------------------------------------------------- eventos curtos e edição


def _agenda_vazia(monkeypatch):
    monkeypatch.setattr(modulo_visualizar, "get_service", lambda escopos: None)
    monkeypatch.setattr(modulo_visualizar, "listar_eventos", lambda *a, **k: [])


def test_evento_de_15_minutos_e_considerado_livre(monkeypatch):
    _agenda_vazia(monkeypatch)
    supervisor = AgenteSupervisor(visualizador=AgenteVisualizar(), criador=MagicMock())
    assert supervisor.verificar_disponibilidade(
        {"inicio": _hora(1, 10).isoformat(), "fim": _hora(1, 10, 15).isoformat()})


def test_visualizacao_normal_continua_ignorando_lacunas_curtas(monkeypatch):
    _agenda_vazia(monkeypatch)
    resposta = AgenteVisualizar().executar_json(
        {"inicio": _hora(1, 10).isoformat(), "fim": _hora(1, 10, 15).isoformat()})
    assert resposta["dados"]["livres"] == []


def _servico_com_evento(inicio, fim):
    servico = MagicMock()
    evento = {"id": "a", "summary": "A", "start": {"dateTime": inicio.isoformat()}, "end": {"dateTime": fim.isoformat()}}
    servico.events().get().execute.return_value = evento
    servico.events().patch().execute.return_value = evento
    servico.events().patch.reset_mock()
    return servico


def test_editar_nao_move_evento_para_o_passado():
    servico = _servico_com_evento(_hora(1, 9), _hora(1, 10))
    resposta = AgenteEditar(servico=servico).executar_json(
        {"id": "a", "inicio": _hora(-1, 9).isoformat(), "fim": _hora(-1, 10).isoformat()})
    assert resposta["status"] == "erro" and "passado" in resposta["erro"]["mensagem"]
    servico.events().patch.assert_not_called()


def test_editar_titulo_de_evento_antigo_continua_valendo():
    servico = _servico_com_evento(_hora(-2, 9), _hora(-2, 10))
    resposta = AgenteEditar(servico=servico).executar_json(
        {"id": "a", "titulo": "Novo", "inicio": _hora(-2, 9).isoformat(), "fim": _hora(-2, 10).isoformat()})
    assert resposta["status"] == "sucesso"


# ---------------------------------------------------------------- planejador


def _tarefa(etapa, titulo):
    return {"etapa": etapa, "titulo": titulo, "objetivo": "o", "entregaveis": "e",
            "demonstracao": "d", "dependencia": etapa - 1, "story_points": 2}


class _Rag:
    def montar_prompt(self, pergunta, **_):
        return "PROMPT"


def test_pergunta_fora_do_assunto_nao_chama_a_llm(monkeypatch):
    llm = MagicMock()
    monkeypatch.setattr(modulo_planejador, "perguntar", llm)
    with pytest.raises(PedidoNaoEntendido):
        AgentePlanejador(rag=_Rag()).executar("qual a receita de bolo de cenoura?", "2026-12-20")
    llm.assert_not_called()


def test_detecta_regras_quebradas():
    plano = [_tarefa(1, "Configurar o ambiente"), _tarefa(2, "Exibição da página de apresentação")]
    assert len(problemas_do_plano(plano, "Um classificador de textos")) == 2
    assert problemas_do_plano([_tarefa(1, "Cadastrar livro")], "API de livros") == []
    assert problemas_do_plano([_tarefa(1, "Ambiente e menu inicial")], "Programa de terminal")


def test_etapa_de_configuracao_e_fundida_e_o_plano_renumerado():
    plano = [_tarefa(1, "Configurar o ambiente"), _tarefa(2, "Cadastrar livro"),
             _tarefa(3, "Listar livros"), _tarefa(4, "Emprestar livro")]
    fundido = fundir_configuracao(plano)
    assert [(t["etapa"], t["titulo"], t["dependencia"]) for t in fundido] == [
        (1, "Cadastrar livro", 0), (2, "Listar livros", 1), (3, "Emprestar livro", 2)]
    assert fundido[0]["entregaveis"] == "e, e" and fundido[0]["story_points"] == 4


def test_funcionalidade_de_configuracao_nao_e_fundida():
    plano = [_tarefa(1, "Configurar alertas de preço"), _tarefa(2, "Ver histórico")]
    assert fundir_configuracao(plano) == plano


def test_plano_com_problema_e_refeito_uma_vez(monkeypatch):
    respostas = [{"tarefas": [_tarefa(1, "Configurar o ambiente")]}, {"tarefas": [_tarefa(1, "Cadastrar livro")]}]
    prompts = []

    def llm(prompt, formato=None):
        prompts.append(prompt)
        return json.dumps(respostas[len(prompts) - 1])

    monkeypatch.setattr(modulo_planejador, "perguntar", llm)
    plano = AgentePlanejador(rag=_Rag()).executar("API de livros", "2026-12-20")
    assert plano["tarefas"][0]["titulo"] == "Cadastrar livro"
    assert len(prompts) == 2 and "CORREÇÃO" in prompts[1]


def test_modelo_escolhido_vai_para_o_planejador(monkeypatch):
    usados = []

    def llm(prompt, formato=None, modelo=None):
        usados.append(modelo)
        return json.dumps({"tarefas": [_tarefa(1, "Cadastrar livro")]})

    monkeypatch.setattr(modulo_planejador, "perguntar", llm)
    AgentePlanejador(rag=_Rag()).executar("API de livros", "2026-12-20", modelo="gemma4:12b-it-q4_K_M")
    assert usados == ["gemma4:12b-it-q4_K_M"]
