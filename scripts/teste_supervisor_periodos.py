"""Teste de tarefas simuladas com os horarios livres reais da agenda."""
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


def main():
    planejador = MagicMock()
    planejador.executar.return_value = {
        "tarefas": [
            {"etapa": 0, "titulo": "Criar HTML"},
            {"etapa": 1, "titulo": "Estilizar CSS"},
            {"etapa": 2, "titulo": "Testar site"},
        ]
    }

    supervisor = AgenteSupervisor(planejador=planejador)
    prazo = (datetime.now(config.FUSO).date() + timedelta(days=7)).isoformat()
    resposta = supervisor.consultar_periodos_projeto("Desenvolver um site", prazo)

    print(json.dumps(resposta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
