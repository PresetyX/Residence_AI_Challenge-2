"""Cada story point vale MINUTOS_POR_STORY_POINT (60 min) no encaixe da agenda."""

from datetime import datetime, timedelta

import pytest

from destrava.core import config
from destrava.core.encaixe_pomodoro import SemEspacoPomodoro, calcular_deficit_minimo, encaixar_tarefas_pomodoro
from destrava.core.pomodoro import MINUTOS_POR_STORY_POINT, minutos_de_trabalho

AGORA = datetime(2026, 11, 18, 8, 0, tzinfo=config.FUSO)


def _livre(horas_inicio, horas_fim, dia=1):
    data = AGORA + timedelta(days=dia)
    inicio = data.replace(hour=horas_inicio, minute=0)
    fim = data.replace(hour=horas_fim, minute=0)
    return {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "duracao_minutos": (fim - inicio).seconds / 60}


def _minutos(evento):
    return round((datetime.fromisoformat(evento["fim"]) - datetime.fromisoformat(evento["inicio"])).total_seconds() / 60)


def test_um_story_point_vale_60_minutos():
    assert MINUTOS_POR_STORY_POINT == 60
    assert minutos_de_trabalho({"story_points": 3}) == 180
    assert minutos_de_trabalho({"titulo": "sem estimativa"}) == 60
    assert minutos_de_trabalho({"story_points": 0}) == 60
    assert minutos_de_trabalho({"story_points": True}) == 60


def test_sem_pomodoro_o_evento_dura_story_points_x_60():
    tarefas = [{"titulo": "A", "story_points": 2}, {"titulo": "B", "story_points": 3}]
    eventos, _ = encaixar_tarefas_pomodoro(tarefas, [_livre(8, 20)], agora=AGORA, usar_pomodoro=False)
    assert [_minutos(e) for e in eventos] == [120, 180]
    assert "Trabalho estimado: 120 minutos" in eventos[0]["descricao"]


def test_com_pomodoro_o_evento_soma_as_pausas():
    # 120 min de foco = 5 blocos de 25/20 min com 4 pausas (3 curtas + 1 longa).
    eventos, detalhes = encaixar_tarefas_pomodoro([{"titulo": "A", "story_points": 2}], [_livre(8, 20)], agora=AGORA)
    foco = sum(s["duracao_minutos"] for s in detalhes[0]["sessoes"] if s["tipo"] == "foco")
    assert foco == 120
    assert _minutos(eventos[0]) == 120 + 3 * 5 + 15


def test_tarefa_maior_que_a_janela_nao_cabe():
    with pytest.raises(SemEspacoPomodoro):
        encaixar_tarefas_pomodoro([{"titulo": "Grande", "story_points": 8}], [_livre(8, 12)], agora=AGORA, usar_pomodoro=False)


def test_deficit_usa_os_story_points():
    # 4h livres - 2h de reserva = 2h utilizáveis; a tarefa pede 5h.
    assert calcular_deficit_minimo([{"titulo": "A", "story_points": 5}], [_livre(8, 12)], agora=AGORA) == 180
