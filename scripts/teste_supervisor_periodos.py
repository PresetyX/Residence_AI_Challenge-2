
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


def main():

    # Simula apenas o Planejador.
    planejador = MagicMock()

    planejador.executar.return_value = {
        "tarefas": [
            {
                "ordem": 1,
                "titulo": "Criar HTML",
                "tipo": "frontend",
                "dificuldade": 1
            },
            {
                "ordem": 2,
                "titulo": "Estilizar CSS",
                "tipo": "frontend",
                "dificuldade": 2
            },
            {
                "ordem": 3,
                "titulo": "Testar site",
                "tipo": "testes",
                "dificuldade": 1
            }
        ]
    }

    # O Visualizar será real, não simulado.
    supervisor = AgenteSupervisor(
        planejador=planejador
    )

    # Prazo de sete dias a partir de hoje.
    prazo = (
        datetime.now(config.FUSO).date()
        + timedelta(days=7)
    ).isoformat()

    resposta = supervisor.consultar_periodos_projeto(
        projeto="Desenvolver um site",
        prazo=prazo
    )

    print(json.dumps(
        resposta,
        indent=2,
        ensure_ascii=False
    ))


if __name__ == "__main__":
    main()
