import pytest

from backend import perfil
from destrava.core import config, pomodoro


@pytest.fixture(autouse=True)
def perfil_isolado(tmp_path, monkeypatch):
    """Cada teste começa com sono e story points de fábrica e um perfis.json vazio."""
    monkeypatch.setattr(perfil, "CAMINHO_PERFIS", tmp_path / "perfis.json")
    monkeypatch.setattr(perfil, "_email_ativo", None)
    monkeypatch.setattr(config, "HORARIO_DORMIR", perfil._PADRAO_DORMIR)
    monkeypatch.setattr(config, "HORARIO_ACORDAR", perfil._PADRAO_ACORDAR)
    monkeypatch.setattr(pomodoro, "MINUTOS_POR_STORY_POINT", perfil._PADRAO_MINUTOS_SP)
