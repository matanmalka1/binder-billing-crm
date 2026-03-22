from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """
    Return the current UTC time as a naive datetime.

    The codebase currently persists naive UTC timestamps in the database
    (SQLAlchemy `DateTime` without `timezone=True`). We derive the value from a
    timezone-aware UTC timestamp to avoid `datetime.utcnow()` deprecations.
    """

    return datetime.now(UTC).replace(tzinfo=None)


def utcnow_aware() -> datetime:
    """
    Return the current UTC time as a timezone-aware datetime.

    Use this for columns declared as DateTime(timezone=True).
    """

    return datetime.now(UTC)

