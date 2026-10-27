from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Block(BaseModel):
    id: str
    title: str
    start: datetime
    end: datetime
    type: Literal["sleep", "event", "manual"] = "event"


class FreeSlot(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: float


class Conflict(BaseModel):
    event_ids: list[str]
    overlap_start: datetime
    overlap_end: datetime


class Visualization(BaseModel):
    busy: list[Block]
    free: list[FreeSlot]
    conflicts: list[Conflict]
    total_free_minutes: float
    total_busy_minutes: float
