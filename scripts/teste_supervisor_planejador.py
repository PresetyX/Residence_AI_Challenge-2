import json
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor


def main():

    # 1. Criamos o Planejador simulado.
    planejador = MagicMock()

    # 2. Definimos o que ele vai devolver.
    planejador.executar.return_value = {
        "tarefas": [
            {
                "ordem": 1,
                "titulo": "Criar estrutura HTML",
                "tipo": "frontend",
                "dificuldade": 1
            },
            {
                "ordem": 2,
                "titulo": "Estilizar pagina com CSS",
                "tipo": "frontend",
                "dificuldade": 2
            },
            {
                "ordem": 3,
                "titulo": "Testar o site",
                "tipo": "testes",
                "dificuldade": 1
            }
        ]
    }

    # 3. Entregamos o mock ao Supervisor.
    supervisor = AgenteSupervisor(planejador=planejador)

    # 4. O Supervisor solicita as tarefas.
    resposta = supervisor.receber_planejamento(
        projeto="Desenvolver um site",
        prazo="2026-11-20"
    )

    # 5. Mostramos o resultado.
    print(json.dumps(resposta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()