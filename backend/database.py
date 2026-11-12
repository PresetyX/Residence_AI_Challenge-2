"""Conexão e inicialização do banco de dados SQLite."""

from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Base declarativa compartilhada pelos modelos persistentes."""


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_BANCO = RAIZ_PROJETO / "data" / "residence_ai.sqlite3"


@lru_cache
def get_engine() -> Engine:
    """Cria o engine SQLite a partir de DATABASE_URL ou do caminho padrão."""
    database_url = "sqlite:///./data/residence_ai.sqlite3"
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )


@lru_cache
def get_session_factory() -> sessionmaker:
    """Retorna a fábrica de sessões síncronas da aplicação."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Cria somente a tabela de histórico caso ela ainda não exista."""
    from backend.history_models import HistoricoTarefa

    engine = get_engine()
    HistoricoTarefa.metadata.create_all(bind=engine, tables=[HistoricoTarefa.__table__])


if __name__ == "__main__":
    init_db()
    print("Banco de dados inicializado com sucesso.")
