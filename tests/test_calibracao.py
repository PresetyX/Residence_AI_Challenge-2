from types import SimpleNamespace
import pytest
from fastapi import HTTPException

from backend.main import (
    HistoricoTarefaRequest,
    ProjetoRequest,
    criar_projeto,
    listar_perguntas_calibracao,
    registrar_historico,
    registrar_respostas_calibracao,
    story_points_perguntas,
)


def test_listar_perguntas_calibracao_devolve_lista_no_contrato():
    resposta = listar_perguntas_calibracao()

    assert len(resposta["perguntas"]) == len(story_points_perguntas)
    assert isinstance(resposta["perguntas"], list)


def test_registrar_respostas_calibracao_devolve_apenas_status():
    respostas = story_points_perguntas.copy()

    resposta = registrar_respostas_calibracao(respostas)

    assert resposta == {"status": "sucesso"}


def test_historico_de_tarefa_devolve_apenas_status():
    registrar_respostas_calibracao([15 * pontos for pontos in story_points_perguntas])

    resposta = registrar_historico(
        HistoricoTarefaRequest(story_points=1, tempo_real_minutos=5)
    )

    assert resposta == {"status": "sucesso"}


def test_calibracao_reinicia_media_e_contagem_de_tarefas():
    registrar_respostas_calibracao([15 * pontos for pontos in story_points_perguntas])
    registrar_historico(HistoricoTarefaRequest(story_points=1, tempo_real_minutos=5))

    resposta = registrar_respostas_calibracao(
        [20 * pontos for pontos in story_points_perguntas]
    )

    assert resposta == {"status": "sucesso"}


def _criar_projeto_com_2_story_points():

    class PlanejadorFalso:
        def executar(self, texto, prazo):
            return {
                "tarefas": [
                    {
                        "etapa": 1,
                        "titulo": "Tarefa",
                        "objetivo": "Objetivo",
                        "entregaveis": "Entrega",
                        "demonstracao": "Demonstração",
                        "story_points": 3,
                    }
                ]
            }

    class PredictorFalso:
        # O backend pede as estimativas do plano inteiro de uma vez.
        def prever_lote(self, tarefas):
            return [2 for _ in tarefas]

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                planejador=PlanejadorFalso(),
                story_points_predictor=PredictorFalso(),
            )
        )
    )
    resposta = criar_projeto(
        ProjetoRequest(texto="Projeto", prazo="2026-12-01"),
        request,
    )

    return resposta["tarefas"][0]["tempo_estimado_minutos"]


def test_sem_calibracao_cada_story_point_vale_60_minutos():
    # 2 story points x MINUTOS_POR_STORY_POINT (60, pomodoro.py).
    assert _criar_projeto_com_2_story_points() == 120


def test_calibracao_define_os_minutos_de_cada_story_point():
    registrar_respostas_calibracao([15 * pontos for pontos in story_points_perguntas])

    assert _criar_projeto_com_2_story_points() == 30


def test_calibracao_aceita_perguntas_puladas():
    respostas = [None, *[45 * pontos for pontos in story_points_perguntas[1:4]], *[None] * 6]

    assert registrar_respostas_calibracao(respostas) == {"status": "sucesso"}
    assert _criar_projeto_com_2_story_points() == 90


def test_calibracao_exige_tres_respostas():
    with pytest.raises(HTTPException, match="pelo menos 3"):
        registrar_respostas_calibracao([30, 60, *[None] * 8])


def test_registrar_historico_rejeita_zero_story_points():
    with pytest.raises(HTTPException, match="maiores que zero"):
        registrar_historico(
            HistoricoTarefaRequest(story_points=0, tempo_real_minutos=5)
        )


@pytest.mark.parametrize(
    "respostas, mensagem",
    [
        (story_points_perguntas[:-1], "número de respostas"),
        ([*story_points_perguntas[:-1], 0], "maiores que zero"),
    ],
)
def test_registrar_respostas_calibracao_rejeita_entrada_invalida(
    respostas: list[int], mensagem: str
):
    with pytest.raises(HTTPException, match=mensagem):
        registrar_respostas_calibracao(respostas)
