"""Etapa 3: mock do Planejador, Visualizar real e Criar real após 'sim'.

Execute: python -m scripts.teste_supervisor_agendamento
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


def main():
    planejador = MagicMock()
    planejador.executar.return_value = {
        "tarefas": [
            {"ordem": 1, "titulo": "Criar HTML", "tipo": "frontend", "dificuldade": 1},
            {"ordem": 2, "titulo": "Estilizar CSS", "tipo": "frontend", "dificuldade": 2},
            {"ordem": 3, "titulo": "Testar site", "tipo": "testes", "dificuldade": 1},
        ]
    }

    supervisor = AgenteSupervisor(planejador=planejador)
    prazo = (datetime.now(config.FUSO).date() + timedelta(days=7)).isoformat()
    resposta = supervisor.preparar_agendamento("Desenvolver um site", prazo)

    print("\n", resposta["mensagem"], "\n")
    if resposta["status"] != "confirmacao":
        return

    print("PRÉVIA DO CRONOGRAMA (NADA FOI CRIADO AINDA):")
    for evento in resposta["dados"]["eventos"]:
        inicio = datetime.fromisoformat(evento["inicio"])
        fim = datetime.fromisoformat(evento["fim"])
        print(f"- {evento['titulo']}: {inicio:%d/%m %H:%M} às {fim:%H:%M}")

    escolha = input("\nCriar esses eventos REAIS na Google Agenda? Digite sim ou não: ").strip().lower()
    if escolha not in ("sim", "não", "nao"):
        print("Resposta inválida. Nenhum evento foi criado.")
        return

    resultado = supervisor.confirmar_agendamento(escolha == "sim")
    print("\n", resultado["mensagem"])
    if resultado.get("dados", {}).get("eventos_criados"):
        for evento in resultado["dados"]["eventos_criados"]:
            print(" -", evento.get("titulo"), evento.get("inicio"))


if __name__ == "__main__":
    main()
