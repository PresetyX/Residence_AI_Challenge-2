
"""
Teste interativo do Agente de Criação com o Google Calendar real.

Usa Gemma 2 para interpretar pedidos em linguagem natural.
Solicita confirmação antes de criar cada evento.
"""

from datetime import datetime

from destrava.agents.criar import AgenteCriar, extrair_dados_evento


def formatar_data(data_iso: str) -> str:
    """Converte a data ISO para um formato legível."""
    return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y às %H:%M")


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
            dados = extrair_dados_evento(pedido)
        except ValueError as erro:
            print(f"\n[erro] {erro}")
            print("Informe novamente o pedido com os dados completos.\n")
            continue

        print("\n=== EVENTO INTERPRETADO ===")
        print("Título:", dados["titulo"])
        print("Início:", formatar_data(dados["inicio"]))
        print("Fim:", formatar_data(dados["fim"]))

        confirmacao = input(
            "\nDigite CRIAR para adicionar o evento à agenda real: "
        ).strip()

        if confirmacao != "CRIAR":
            print("Criação cancelada.\n")
            continue

        try:
            resultado = agente.executar(dados)
        except Exception as erro:
            print(f"\n[erro] Não foi possível confirmar a criação: {erro}")
            print("Verifique a agenda antes de tentar novamente.\n")
            continue

        print("\n=== EVENTO CRIADO ===")
        print("ID:", resultado["id"])
        print("Título:", resultado.get("summary"))
        print("Início:", resultado.get("start", {}).get("dateTime"))
        print("Fim:", resultado.get("end", {}).get("dateTime"))
        print("Link:", resultado.get("htmlLink", "Não disponível"))
        print()


if __name__ == "__main__":
    main()
