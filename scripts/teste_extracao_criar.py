
"""
Teste interativo da extração de eventos com Gemma 2.

Não acessa o Google Calendar nem cria eventos reais.
"""

from destrava.agents.criar import extrair_dados_evento


def main():
    """Recebe solicitações do terminal e mostra os dados extraídos."""

    print("=== DESTRAVA - TESTE DO AGENTE DE CRIAÇÃO ===")
    print("Digite 'sair' para encerrar.\n")

    while True:
        pergunta = input("Você: ").strip()

        if pergunta.lower() == "sair":
            break

        if not pergunta:
            continue

        try:
            dados = extrair_dados_evento(pergunta)

            print("\n=== EVENTO INTERPRETADO ===")
            print("Título:", dados["titulo"])
            print("Início:", dados["inicio"])
            print("Fim:", dados["fim"])
            print()

        except ValueError as erro:
            print(f"\n[erro] {erro}\n")


if __name__ == "__main__":
    main()
