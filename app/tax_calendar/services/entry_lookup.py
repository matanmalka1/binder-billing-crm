"""TaxCalendarEntry lookup helpers for transitional FK wiring."""

from sqlalchemy.orm import Session

from app.common.enums import ObligationType
from app.tax_calendar.models.tax_calendar_entry import TaxCalendarEntry


def _value(obligation_type: ObligationType | str) -> str:
    return (
        obligation_type.value
        if isinstance(obligation_type, ObligationType)
        else obligation_type
    )


def find_periodic_entry_id(
    db: Session,
    obligation_type: ObligationType | str,
    period: str,
    period_months_count: int,
) -> int | None:
    entry = find_periodic_entry(db, obligation_type, period, period_months_count)
    return entry.id if entry else None


def find_periodic_entry(
    db: Session,
    obligation_type: ObligationType | str,
    period: str,
    period_months_count: int,
) -> TaxCalendarEntry | None:
    entry = (
        db.query(TaxCalendarEntry)
        .filter(TaxCalendarEntry.obligation_type == _value(obligation_type))
        .filter(TaxCalendarEntry.period == period)
        .filter(TaxCalendarEntry.period_months_count == period_months_count)
        .one_or_none()
    )
    return entry


def find_annual_entry_id(db: Session, tax_year: int) -> int | None:
    entry = (
        db.query(TaxCalendarEntry.id)
        .filter(TaxCalendarEntry.obligation_type == ObligationType.ANNUAL_REPORT.value)
        .filter(TaxCalendarEntry.tax_year == tax_year)
        .one_or_none()
    )
    return entry[0] if entry else None
