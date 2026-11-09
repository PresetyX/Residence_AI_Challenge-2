"""Contrato simples: Planejador simulado, Visualizar real e Criar após confirmação.

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
            {"etapa": 0, "titulo": "Criar HTML"},
            {"etapa": 1, "titulo": "Estilizar CSS"},
            {"etapa": 2, "titulo": "Testar site"},
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
        duracao = round((fim - inicio).total_seconds() / 60)
        print(f"- {evento['titulo']}: {inicio:%d/%m %H:%M} às {fim:%H:%M} ({duracao} min)")

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
