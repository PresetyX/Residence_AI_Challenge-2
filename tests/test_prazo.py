"""Interpretação do prazo do projeto em linguagem natural (destrava/core/prazo.py)."""

from datetime import date, datetime

import pytest

from destrava.core import config
from destrava.core.prazo import interpretar_prazo

# Quarta-feira, 18/11/2026.
AGORA = datetime(2026, 11, 18, 10, 0, tzinfo=config.FUSO)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Quero um app de receitas com prazo 2026-12-20", date(2026, 12, 20)),
        ("app de receitas até 20/12/2026", date(2026, 12, 20)),
        ("app de receitas até 20/12/26", date(2026, 12, 20)),
        ("app de receitas até 20/12", date(2026, 12, 20)),
        ("entregar dia 10/01", date(2027, 1, 10)),
        ("até 20 de dezembro", date(2026, 12, 20)),
        ("até 5 de março de 2027", date(2027, 3, 5)),
        ("até dezembro", date(2026, 12, 31)),
        ("preciso entregar até amanhã", date(2026, 11, 19)),
        ("até depois de amanhã", date(2026, 11, 20)),
        ("tenho que entregar hoje mesmo", date(2026, 11, 18)),
        ("tenho uma semana para fazer", date(2026, 11, 25)),
        ("tenho 1 semana", date(2026, 11, 25)),
        ("tenho duas semanas", date(2026, 12, 2)),
        ("em 3 semanas", date(2026, 12, 9)),
        ("daqui a 10 dias", date(2026, 11, 28)),
        ("dentro de 2 meses", date(2027, 1, 18)),
        ("tenho um mês", date(2026, 12, 18)),
        ("prazo de um ano", date(2027, 11, 18)),
        ("uma quinzena", date(2026, 12, 3)),
        ("semana que vem", date(2026, 11, 29)),
        ("até o fim da semana", date(2026, 11, 22)),
        ("até o fim do mês", date(2026, 11, 30)),
        ("mês que vem", date(2026, 12, 31)),
        ("até o fim do ano", date(2026, 12, 31)),
        ("até sexta", date(2026, 11, 20)),
        ("até quarta-feira", date(2026, 11, 25)),
    ],
)
def test_interpreta_o_prazo(texto, esperado):
    assert interpretar_prazo(texto, AGORA) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "Quero criar um app de receitas",
        "tenho 10 horas livres",
        "banana com azeite",
        "reunião das 13:30 às 14:00",
        "",
    ],
)
def test_sem_prazo_devolve_none(texto):
    assert interpretar_prazo(texto, AGORA) is None


def test_data_inexistente_gera_erro():
    with pytest.raises(ValueError, match="31/02"):
        interpretar_prazo("até 31/02", AGORA)
