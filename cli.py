"""CLI do Destrava: conversa com os agentes da agenda e mostra o JSON.

Todos os agentes devolvem o mesmo formato (ver destrava/core/resposta.py):
agente, status, acao, mensagem, periodo, dados, fluxo (inicio/meio/fim) e erro.

Uso:
    python cli.py            # mostra o JSON completo
    python cli.py --texto    # mostra só a mensagem final
"""

import sys
from datetime import datetime

from destrava.agents.criar import AgenteCriar
from destrava.agents.visualizar import AgenteVisualizar


def _formatar(data_iso: str) -> str:
    return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y às %H:%M")


def confirmar_criacao(dados: dict) -> bool:
    """Mostra o evento interpretado e só cria se o usuário digitar CRIAR."""
    print("\n=== EVENTO INTERPRETADO ===")
    print("Título:", dados["titulo"])
    print("Início:", _formatar(dados["inicio"]))
    print("Fim:   ", _formatar(dados["fim"]))
    return input("\nDigite CRIAR para adicionar à agenda real: ").strip() == "CRIAR"


AGENTES = {
    "1": ("visualizar", lambda pedido: AgenteVisualizar().executar_por_texto(pedido)),
    "2": (
        "criar",
        lambda pedido: AgenteCriar().executar_por_texto(
            pedido, confirmar=confirmar_criacao
        ),
    ),
}


def main():
    so_texto = "--texto" in sys.argv[1:]

    print("=== DESTRAVA ===")
    print("Agentes: 1 = visualizar, 2 = criar. Digite 'sair' para encerrar.\n")

    while True:
        escolha = input("Agente: ").strip().lower()
        if escolha == "sair":
            break
        if escolha not in AGENTES:
            print("Opção inválida.\n")
            continue

        pedido = input("Você: ").strip()
        if not pedido:
            continue
        if pedido.lower() == "sair":
            break

        _, executar = AGENTES[escolha]
        resposta = executar(pedido)

        print()
        print(resposta.mensagem if so_texto else resposta.para_json())
        print()


if __name__ == "__main__":
    main()
