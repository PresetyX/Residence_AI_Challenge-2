"""Teste interativo com Gemma e Google Calendar reais.

Execute na raiz do repositório: python -m scripts.teste_supervisor_real
Não cria eventos até o usuário responder "sim" à prévia explícita.
"""

from destrava.agents.supervisor import AgenteSupervisor


def main():
    supervisor = AgenteSupervisor()
    print("Supervisor do Destrava — consulta e criação com confirmação. Digite 'sair' para encerrar.\n")
    while True:
        pedido = input("Você: ").strip()
        if pedido.casefold() in {"sair", "exit", "quit"}:
            break
        resultado = supervisor.executar(pedido)
        print(f"\nDestrava: {resultado['mensagem']}\n")


if __name__ == "__main__":
    main()
