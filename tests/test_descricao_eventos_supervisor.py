"""Regressoes da descricao detalhada das tarefas. Sem chamadas reais ao Google."""

from datetime import datetime, timedelta, time
from unittest.mock import MagicMock

from destrava.core import config
from destrava.core.encaixe_pomodoro import encaixar_tarefas_pomodoro
from destrava.agents.criar import criar_evento_google


def _horarios_livres():
    dia = (datetime.now(config.FUSO) + timedelta(days=2)).date()
    inicio = datetime.combine(dia, time(8, 0), tzinfo=config.FUSO)
    fim = datetime.combine(dia, time(20, 0), tzinfo=config.FUSO)
    return [{"inicio": inicio.isoformat(), "fim": fim.isoformat()}]


def _tarefa_completa():
    return {
        "etapa": 4,
        "titulo": "Implementar login",
        "objetivo": "Permitir que o usuario entre no sistema.",
        "entregaveis": "Tela de login e rota de autenticacao.",
        "demonstracao": "Realizar login e validar credenciais.",
        "story_points": 2,
    }


def test_pomodoro_inclui_campos_e_ciclos():
    eventos, detalhes = encaixar_tarefas_pomodoro(
        [_tarefa_completa()], _horarios_livres(), usar_pomodoro=True
    )
    descricao = eventos[0]["descricao"]
    assert "Etapa 4 — Implementar login" in descricao
    assert "Objetivo: Permitir que o usuario entre no sistema." in descricao
    assert "Entregáveis: Tela de login e rota de autenticacao." in descricao
    assert "Demonstração: Realizar login e validar credenciais." in descricao
    assert "Trabalho estimado: 120 minutos." in descricao
    assert "Técnica Pomodoro:" in descricao
    assert "Ciclos:" in descricao
    assert "Foco" in descricao
    assert "Pausas: 30 minutos" in descricao
    assert len(detalhes[0]["sessoes"]) > 1


def test_sem_pomodoro_inclui_campos_e_duracao_real():
    eventos, detalhes = encaixar_tarefas_pomodoro(
        [_tarefa_completa()], _horarios_livres(), usar_pomodoro=False
    )
    descricao = eventos[0]["descricao"]
    assert "Etapa 4 — Implementar login" in descricao
    assert "Objetivo:" in descricao
    assert "Entregáveis:" in descricao
    assert "Demonstração:" in descricao
    assert "Trabalho estimado: 120 minutos." in descricao
    assert "Técnica Pomodoro: não utilizada" in descricao
    assert "Ciclos:" not in descricao
    assert detalhes == []
    duracao = datetime.fromisoformat(eventos[0]["fim"]) - datetime.fromisoformat(eventos[0]["inicio"])
    assert duracao == timedelta(minutes=120)


def test_campos_opcionais_ausentes_nao_sao_inventados():
    eventos, _ = encaixar_tarefas_pomodoro(
        [{"titulo": "Revisar API"}], _horarios_livres(), usar_pomodoro=True
    )
    descricao = eventos[0]["descricao"]
    assert "Tarefa: Revisar API" in descricao
    assert "Trabalho estimado: 60 minutos." in descricao
    assert "Objetivo:" not in descricao
    assert "Entregáveis:" not in descricao
    assert "Demonstração:" not in descricao


def test_etapa_zero_e_campos_em_branco():
    eventos, _ = encaixar_tarefas_pomodoro(
        [{"etapa": 0, "titulo": " Configurar ambiente ", "objetivo": " ", "story_points": 1}],
        _horarios_livres(), usar_pomodoro=False
    )
    descricao = eventos[0]["descricao"]
    assert "Etapa 0 — Configurar ambiente" in descricao
    assert "Objetivo:" not in descricao


def test_google_recebe_a_mesma_descricao_sem_chamada_real():
    eventos, _ = encaixar_tarefas_pomodoro(
        [_tarefa_completa()], _horarios_livres(), usar_pomodoro=True
    )
    servico = MagicMock()
    servico.events.return_value.insert.return_value.execute.return_value = {"id": "id-falso"}
    criar_evento_google(eventos[0], servico)
    kwargs = servico.events.return_value.insert.call_args.kwargs
    assert kwargs["calendarId"] == "primary"
    assert kwargs["body"]["description"] == eventos[0]["descricao"]
