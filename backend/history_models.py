"""Modelo dos story points associados aos eventos da agenda."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class EventoStoryPoints(Base):
    """Story points disponíveis para um evento da agenda."""

    __tablename__ = "eventos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    storypoints: Mapped[int] = mapped_column(Integer, nullable=True)
