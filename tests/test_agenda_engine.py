from datetime import datetime

from destrava.core.agenda_engine import build_visualization


def test_sleep_is_not_free():
    start = datetime(2026, 10, 28, 0, 0)
    end = datetime(2026, 10, 29, 0, 0)

    result = build_visualization([], start, end)

    assert all(
        not (slot.start.hour >= 23 or slot.end.hour <= 7)
        for slot in result.free
    )


def test_conflict_is_detected():
    start = datetime(2026, 10, 28, 8, 0)
    end = datetime(2026, 10, 28, 12, 0)

    events = [
        {
            "id": "1",
            "title": "Aula",
            "start": datetime(2026, 10, 28, 9, 0),
            "end": datetime(2026, 10, 28, 10, 0),
            "type": "event",
        },
        {
            "id": "2",
            "title": "Reunião",
            "start": datetime(2026, 10, 28, 9, 30),
            "end": datetime(2026, 10, 28, 11, 0),
            "type": "event",
        },
    ]

    result = build_visualization(events, start, end)

    assert len(result.conflicts) == 1
