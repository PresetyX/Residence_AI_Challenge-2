from datetime import datetime, timedelta

from destrava.core.agenda_engine import build_visualization
from destrava.core.google_calendar import get_events
from destrava.core.llm import explain_visualization
from destrava.core.models import Visualization


def parse_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            "Use o formato ISO 8601. Exemplo: 2026-10-28T00:00:00-03:00"
        ) from error


def print_visualization(visualization: Visualization) -> None:
    print("\n=== HORÁRIOS OCUPADOS ===")

    for block in visualization.busy:
        print(
            f"- {block.title}: "
            f"{block.start.strftime('%d/%m %H:%M')} até "
            f"{block.end.strftime('%d/%m %H:%M')}"
        )

    print("\n=== HORÁRIOS LIVRES ===")

    for slot in visualization.free:
        print(
            f"- {slot.start.strftime('%d/%m %H:%M')} até "
            f"{slot.end.strftime('%d/%m %H:%M')} "
            f"({slot.duration_minutes:.0f} min)"
        )

    print("\n=== CONFLITOS ===")

    if not visualization.conflicts:
        print("- Nenhum conflito encontrado.")
    else:
        for conflict in visualization.conflicts:
            print(
                f"- Eventos {', '.join(conflict.event_ids)} conflitam entre "
                f"{conflict.overlap_start.strftime('%d/%m %H:%M')} e "
                f"{conflict.overlap_end.strftime('%d/%m %H:%M')}"
            )

    print("\n=== RESUMO ===")
    print(f"Tempo livre: {visualization.total_free_minutes:.0f} minutos")
    print(f"Tempo ocupado: {visualization.total_busy_minutes:.0f} minutos")


def main():
    print("=== Destrava - Agente de Visualização ===\n")

    period = input(
        "Período [1 = hoje, 2 = amanhã, 3 = semana, 4 = personalizado]: "
    ).strip()

    now = datetime.now().astimezone()

    if period == "1":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif period == "2":
        start = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=1)
    elif period == "3":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    elif period == "4":
        start = parse_date(input("Data inicial (ISO 8601): "))
        end = parse_date(input("Data final (ISO 8601): "))
    else:
        print("Opção inválida.")
        return

    print("\nBuscando eventos no Google Calendar...")
    events = get_events(start, end)
    print(f"Eventos encontrados: {len(events)}")

    visualization = build_visualization(events, start, end)
    print_visualization(visualization)

    explain = input("\nQuer uma explicação com o modelo local? [s/N]: ")

    if explain.lower() in ["s", "sim", "y", "yes"]:
        print("\nCarregando modelo local e gerando explicação...\n")

        explanation = explain_visualization(
            user_message=(
                "Explique minha rotina e destaque horários livres, "
                "ocupados e conflitos."
            ),
            visualization=visualization,
        )

        print("=== EXPLICAÇÃO DA IA ===")
        print(explanation)


if __name__ == "__main__":
    main()
