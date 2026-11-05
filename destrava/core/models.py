"""
Estruturas de dados da visualização da agenda.

Usadas pelo agenda_engine.py (que calcula) e pelos agentes (que exibem).
Todas as datas são datetime com fuso horário (config.FUSO).
"""

from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator

from destrava.core import config

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
        if (self.inicio.tzinfo is None) != (self.fim.tzinfo is None):
            raise ValueError("inicio e fim devem ter fuso, ou os dois não ter.")
        if self.fim < self.inicio:
            raise ValueError("A data final não pode ser anterior à inicial.")
        if self.fim == self.inicio:
            self.fim = self.inicio + timedelta(days=1)
        return self


class PedidoCriacao(BaseModel):
    """Pedido de entrada do agente de criação: o evento a criar.

    Datas sem fuso são consideradas no horário de config.FUSO. Não aceita
    título vazio, início igual ou posterior ao fim, nem evento no passado.
    """

    titulo: str
    inicio: datetime
    fim: datetime

    @field_validator("titulo", mode="before")
    @classmethod
    def _titulo_obrigatorio(cls, valor):
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("O título do evento é obrigatório.")
        return valor.strip()

    @field_validator("inicio", "fim", mode="before")
    @classmethod
    def _horario_obrigatorio(cls, valor):
        if valor is None or valor == "":
            raise ValueError("Início e fim são obrigatórios.")
        return valor

    @field_validator("inicio", "fim")
    @classmethod
    def _no_fuso_do_projeto(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None:
            return valor.replace(tzinfo=config.FUSO)
        return valor.astimezone(config.FUSO)

    @model_validator(mode="after")
    def _horarios_coerentes(self):
        if self.inicio >= self.fim:
            raise ValueError("O início deve ser anterior ao fim.")
        if self.inicio <= datetime.now(config.FUSO):
            raise ValueError("Não é permitido criar eventos no passado.")
        return self


class Periodo(BaseModel):
    """Período tratado pelo agente."""

    inicio: datetime
    fim: datetime
    duracao_minutos: float


class Etapa(BaseModel):
    """Uma etapa do fluxo do agente."""

    etapa: str
    status: Literal["ok", "erro", "pendente"] = "pendente"
    detalhe: Any = None


class Fluxo(BaseModel):
    """As três etapas do fluxo de um agente: início, meio e fim."""

    inicio: Etapa
    meio: Etapa
    fim: Etapa


class ErroInfo(BaseModel):
    """Erro que interrompeu o fluxo."""

    tipo: str
    mensagem: str


class RespostaAgente(BaseModel):
    """Resposta JSON padrão dos agentes de visualizar e criar."""

    status: Literal["sucesso", "erro"]
    acao: str
    periodo: Periodo | None = None
    dados: dict[str, Any] | None = None
    fluxo: Fluxo
    erro: ErroInfo | None = None

