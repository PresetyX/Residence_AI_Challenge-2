from datetime import datetime

from destrava.core.agenda_engine import build_visualization
from destrava.core.google_calendar import get_events


class VisualizationAgent:
    def run(self, start: datetime, end: datetime) -> dict:
        if end <= start:
            raise ValueError("A data final deve ser posterior à inicial.")

        events = get_events(start, end)

        visualization = build_visualization(
            events=events,
            start=start,
            end=end,
        )

        return visualization.model_dump(mode="json")
