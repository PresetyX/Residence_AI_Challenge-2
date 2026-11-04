import pytest
from pydantic import ValidationError

from destrava.core.models import PedidoPlanejamento


def test_supervisor_recebe_json_valido():
    entrada = {
        "projeto": "Desenvolver uma API REST",
        "prazo": "2026-11-15",
        "tarefas": [
            {
                "id": "T001",
                "titulo": "Implementar as rotas",
                "categoria": "programacao",
                "tamanho": 2,
                "complexidade": 7,
                "tempo_estimado": 110
            }
        ]
    }

    resultado = PedidoPlanejamento.model_validate(entrada)

    assert resultado.projeto == "Desenvolver uma API REST"
    assert len(resultado.tarefas) == 1
    assert resultado.tarefas[0].tempo_estimado == 110


def test_supervisor_rejeita_complexidade_invalida():
    entrada = {
        "projeto": "Desenvolver uma API REST",
        "prazo": "2026-11-15",
        "tarefas": [
            {
                "id": "T001",
                "titulo": "Implementar as rotas",
                "categoria": "programacao",
                "tamanho": 2,
                "complexidade": 15,
                "tempo_estimado": 110
            }
        ]
    }

    with pytest.raises(ValidationError):
        PedidoPlanejamento.model_validate(entrada)