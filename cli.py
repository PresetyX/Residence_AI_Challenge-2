"""CLI do Destrava: agente de visualização da agenda.

Contrato: recebe qualquer pergunta em texto livre sobre a agenda,
extrai o período com o LLM, busca os eventos no Google Calendar,
calcula ocupados/livres/conflitos e devolve uma explicação em português.
"""

from destrava.agents.visualizar import AgenteVisualizar


def main():
    print("Digite sua pergunta sobre a agenda (ou 'sair').\n")

    agente = AgenteVisualizar()

    while True:
        pergunta = input("Você: ").strip()

        if pergunta.lower() in ("sair", "exit", "quit"):
            break
        if not pergunta:
            continue

        try:
            resposta = agente.executar_por_texto(pergunta)
            print(f"\n{resposta}\n")
        except Exception as erro:
            print(f"\n[erro] {erro}\n")


if __name__ == "__main__":
    main()