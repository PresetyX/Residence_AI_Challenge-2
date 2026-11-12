"""Modelo para registrar dados reais de execução de tarefas."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class HistoricoTarefa(Base):
    """Registro de story points estimados e tempo real de uma tarefa."""

    __tablename__ = "historico"
    __table_args__ = (
        CheckConstraint(
            "story_points >= 0",
            name="ck_historico_story_points_nao_negativo",
        ),
        CheckConstraint(
            "tempo_real_minutos >= 0",
            name="ck_historico_tempo_real_nao_negativo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    story_points: Mapped[int] = mapped_column(Integer, nullable=False)
    tempo_real_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
