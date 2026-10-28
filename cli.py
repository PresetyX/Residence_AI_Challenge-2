"""CLI do Destrava: agente de visualização da agenda.

Fluxo:
    1. Usuário escolhe o período (hoje, amanhã, semana ou personalizado).
    2. O agente busca os eventos no Google Calendar (somente leitura).
    3. O agente calcula ocupados, livres e conflitos.
    4. O LLM local explica a rotina em português.
"""

from datetime import datetime, timedelta

from destrava.agents.visualizar import AgenteVisualizar, responder


def parse_date(value: str) -> datetime:
    """Converte uma string ISO 8601 em datetime."""
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            "Use o formato ISO 8601. Exemplo: 2026-10-28T00:00:00-03:00"
        ) from error


def main():
    periodo = input(
        "Período [1 = hoje, 2 = amanhã, 3 = semana, 4 = personalizado]: "
    ).strip()

    agora = datetime.now().astimezone()

    if periodo == "1":
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(days=1)
    elif periodo == "2":
        inicio = (agora + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        fim = inicio + timedelta(days=1)
    elif periodo == "3":
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(days=7)
    elif periodo == "4":
        inicio = parse_date(input("Data inicial (ISO 8601): "))
        fim = parse_date(input("Data final (ISO 8601): "))
    else:
        print("Opção inválida.")
        return

    agente = AgenteVisualizar()

    try:
        resultado = agente.executar(inicio, fim)
    except Exception as erro:
        print(f"[erro] {erro}")
        return

    pergunta = (
        "Explique minha rotina e destaque horários livres, "
        "ocupados e conflitos."
    )

    try:
        explicacao = responder(pergunta, resultado)
    except Exception as erro:
        print(f"[erro] {erro}")
        return

    print(explicacao)


if __name__ == "__main__":
    main()