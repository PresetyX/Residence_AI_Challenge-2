"""
Estruturas de dados da visualização da agenda.

Usadas pelo agenda_engine.py (que calcula) e pelos agentes (que exibem).
Todas as datas são datetime com fuso horário (config.FUSO).
"""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, model_validator


class Bloco(BaseModel):
    """Um intervalo de tempo da agenda: um evento, um evento de dia inteiro ou o sono."""

    id: str
    titulo: str
    inicio: datetime
    fim: datetime
    tipo: Literal["sono", "evento", "dia_inteiro", "manual"] = "evento"


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


class PedidoVisualizacao(BaseModel):
    """Pedido de entrada do agente de visualização: o período a consultar."""

    inicio: datetime
    fim: datetime

    @model_validator(mode="after")
    def _fim_depois_inicio(self):
        if self.fim < self.inicio:
            raise ValueError("A data final não deve ser anterior a atual")
        if self.fim == self.inicio:
            self.fim = self.inicio + timedelta(days=1)
        return self
