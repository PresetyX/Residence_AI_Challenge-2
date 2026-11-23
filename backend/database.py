import sqlite3
from pathlib import Path

from sqlalchemy.orm import DeclarativeBase


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_BANCO_EVENTOS = RAIZ_PROJETO / "data" / "eventos.db"
TABELA_EVENTOS = "eventos"


class Base(DeclarativeBase):
    pass


def inicializar_banco_eventos() -> None:
    CAMINHO_BANCO_EVENTOS.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(CAMINHO_BANCO_EVENTOS) as conexao:
        conexao.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABELA_EVENTOS} (
                id TEXT PRIMARY KEY,
                storypoints INTEGER
            )
            """
        )


def buscar_storypoints_evento(id_evento: str) -> int | None:
    inicializar_banco_eventos()
    with sqlite3.connect(CAMINHO_BANCO_EVENTOS) as conexao:
        resultado = conexao.execute(
            f"SELECT storypoints FROM {TABELA_EVENTOS} WHERE id = ?",
            (id_evento,),
        ).fetchone()
    return None if resultado is None else resultado[0]
