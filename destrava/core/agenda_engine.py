from datetime import datetime, timedelta

from destrava.core.models import Block, Conflict, FreeSlot, Visualization


def merge_blocks(blocks: list[Block]) -> list[Block]:
    ordered = sorted(blocks, key=lambda block: block.start)
    merged: list[Block] = []

    for block in ordered:
        if merged and block.start <= merged[-1].end:
            merged[-1].end = max(merged[-1].end, block.end)
        else:
            merged.append(block.model_copy())

    return merged


def add_sleep_blocks(
    start: datetime,
    end: datetime,
    sleep_start_hour: int = 23,
    sleep_end_hour: int = 7,
) -> list[Block]:
    sleep_blocks = []
    current_day = start.replace(hour=0, minute=0, second=0, microsecond=0)

    while current_day <= end:
        sleep_start = current_day.replace(hour=sleep_start_hour)
        sleep_end = sleep_start + timedelta(days=1)
        sleep_end = sleep_end.replace(hour=sleep_end_hour)

        sleep_blocks.append(
            Block(
                id=f"sleep-{sleep_start.isoformat()}",
                title="Sono",
                start=sleep_start,
                end=sleep_end,
                type="sleep",
            )
        )

        current_day += timedelta(days=1)

    return sleep_blocks


def calculate_free_slots(
    busy: list[Block],
    start: datetime,
    end: datetime,
    minimum_minutes: int = 15,
) -> list[FreeSlot]:
    merged = merge_blocks(busy)
    free: list[FreeSlot] = []
    cursor = start

    for block in merged:
        if block.start > cursor:
            duration = (block.start - cursor).total_seconds() / 60

            if duration >= minimum_minutes:
                free.append(
                    FreeSlot(
                        start=cursor,
                        end=block.start,
                        duration_minutes=duration,
                    )
                )

        cursor = max(cursor, block.end)

    remaining = (end - cursor).total_seconds() / 60

    if remaining >= minimum_minutes:
        free.append(
            FreeSlot(
                start=cursor,
                end=end,
                duration_minutes=remaining,
            )
        )

    return free


def find_conflicts(events: list[Block]) -> list[Conflict]:
    conflicts: list[Conflict] = []

    for index, first in enumerate(events):
        for second in events[index + 1:]:
            if first.start < second.end and second.start < first.end:
                conflicts.append(
                    Conflict(
                        event_ids=[first.id, second.id],
                        overlap_start=max(first.start, second.start),
                        overlap_end=min(first.end, second.end),
                    )
                )

    return conflicts


def build_visualization(
    events: list[dict],
    start: datetime,
    end: datetime,
) -> Visualization:
    event_blocks = [Block(**event) for event in events]
    sleep_blocks = add_sleep_blocks(start, end)

    busy = merge_blocks(event_blocks + sleep_blocks)
    free = calculate_free_slots(busy, start, end)
    conflicts = find_conflicts(event_blocks)

    total_free = sum(slot.duration_minutes for slot in free)
    total_busy = sum(
        (block.end - block.start).total_seconds() / 60
        for block in busy
    )

    return Visualization(
        busy=busy,
        free=free,
        conflicts=conflicts,
        total_free_minutes=total_free,
        total_busy_minutes=total_busy,
    )
