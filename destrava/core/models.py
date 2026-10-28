"""
Estruturas de dados da visualização da agenda.

Usadas pelo agenda_engine.py (que calcula) e pelos agentes (que exibem).
Todas as datas são datetime com fuso horário (config.FUSO).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Bloco(BaseModel):
    """Um intervalo de tempo ocupado: um evento da agenda ou o sono."""

    id: str
    titulo: str
    inicio: datetime
    fim: datetime
    tipo: Literal["sono", "evento", "manual"] = "evento"


class HorarioLivre(BaseModel):
    """Um intervalo livre com pelo menos a duração mínima configurada."""

    inicio: datetime
    fim: datetime
    duracao_minutos: float


class Conflito(BaseModel):
    """Dois eventos que se sobrepõem, com o trecho em que se sobrepõem."""

    ids_eventos: list[str]
    inicio_sobreposicao: datetime
    fim_sobreposicao: datetime


class Visualizacao(BaseModel):
    """Resultado completo da visualização de um período."""

    ocupados: list[Bloco]
    livres: list[HorarioLivre]
    conflitos: list[Conflito]
    total_minutos_livres: float
    total_minutos_ocupados: float
