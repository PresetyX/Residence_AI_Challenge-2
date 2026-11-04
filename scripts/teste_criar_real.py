
"""
Teste interativo do Agente de Criação com o Google Calendar real.

Usa Gemma 2 para interpretar pedidos em linguagem natural.
Solicita confirmação antes de criar cada evento e mostra a resposta em texto.
Para testar o caminho em JSON (sem LLM), use: python cli.py (agente 2).

Uso:
    python -m scripts.teste_criar_real
"""

from datetime import datetime

from destrava.agents.criar import AgenteCriar


def formatar_data(data_iso: str) -> str:
    """Converte a data ISO para um formato legível."""
    return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y às %H:%M")


def confirmar(dados: dict) -> bool:
    """Mostra o evento interpretado e pede a confirmação do usuário."""
    print("\n=== EVENTO INTERPRETADO ===")
    print("Título:", dados["titulo"])
    print("Início:", formatar_data(dados["inicio"]))
    print("Fim:", formatar_data(dados["fim"]))

    return input(
        "\nDigite CRIAR para adicionar o evento à agenda real: "
    ).strip() == "CRIAR"


def main():
    """Recebe pedidos, confirma os dados e cria eventos reais."""

    agente = AgenteCriar()

    print("=== DESTRAVA - AGENTE DE CRIAÇÃO ===")
    print("Digite 'sair' para encerrar.\n")

    while True:
        pedido = input("Você: ").strip()

        if pedido.lower() == "sair":
            break

        if not pedido:
            continue

        try:
            resposta = agente.executar_por_texto(pedido, confirmar=confirmar)
        except Exception as erro:
            print(f"\n[erro] {erro}\n")
            continue

        print("\n=== RESPOSTA ===")
        print(resposta)
        print()


if __name__ == "__main__":
    main()
