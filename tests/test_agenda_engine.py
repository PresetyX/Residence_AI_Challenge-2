from datetime import datetime

from destrava.core.agenda_engine import montar_visualizacao


def test_sono_nao_e_livre():
    inicio = datetime(2026, 10, 28, 0, 0)
    fim = datetime(2026, 10, 29, 0, 0)

    resultado = montar_visualizacao([], inicio, fim)

    assert all(
        not (livre.inicio.hour >= 23 or livre.fim.hour <= 7)
        for livre in resultado.livres
    )


def test_conflito_e_detectado():
    inicio = datetime(2026, 10, 28, 8, 0)
    fim = datetime(2026, 10, 28, 12, 0)

    eventos = [
        {
            "id": "1",
            "titulo": "Aula",
            "inicio": datetime(2026, 10, 28, 9, 0),
            "fim": datetime(2026, 10, 28, 10, 0),
            "tipo": "evento",
        },
        {
            "id": "2",
            "titulo": "Reunião",
            "inicio": datetime(2026, 10, 28, 9, 30),
            "fim": datetime(2026, 10, 28, 11, 0),
            "tipo": "evento",
        },
    ]

    resultado = montar_visualizacao(eventos, inicio, fim)

    assert len(resultado.conflitos) == 1
