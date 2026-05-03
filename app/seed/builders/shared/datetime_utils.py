from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random


def random_past_datetime(rng: Random, min_days: int, max_days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=rng.randint(min_days, max_days))


def random_datetime_between(rng: Random, start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    seconds = max(1, int((end - start).total_seconds()))
    return start + timedelta(seconds=rng.randint(0, seconds))


def clamp_to_now(dt: datetime) -> datetime:
    now = datetime.now(UTC)
    return min(dt, now)
