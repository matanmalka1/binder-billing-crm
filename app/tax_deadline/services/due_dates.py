"""Tax deadline due-date derivation."""

from datetime import date

from sqlalchemy.orm import Session

from app.common.enums import VatType
from app.core.exceptions import AppError
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.vat_reports.services.constants import VAT_STATUTORY_DEADLINE_DAY


def _parse_period(period: str | None) -> tuple[int, int]:
    if not period:
        raise AppError("יש לבחור תקופת דיווח", "TAX_DEADLINE.MISSING_PERIOD")
    try:
        year_part, month_part = period.split("-", 1)
        year = int(year_part)
        month = int(month_part)
    except ValueError as exc:
        raise AppError("תקופת הדיווח אינה תקינה", "TAX_DEADLINE.INVALID_PERIOD") from exc
    if month < 1 or month > 12:
        raise AppError("תקופת הדיווח אינה תקינה", "TAX_DEADLINE.INVALID_PERIOD")
    return year, month


def _filing_month(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = month - 1 + offset
    return year + month_index // 12, month_index % 12 + 1


def resolve_vat_due_date(db: Session, client_record, period: str | None) -> date:
    """Resolve the conservative statutory VAT due date for a reporting period."""
    legal_entity = LegalEntityRepository(db).get_by_id(client_record.legal_entity_id)
    vat_type = legal_entity.vat_reporting_frequency if legal_entity else None
    if vat_type in (None, VatType.EXEMPT):
        raise AppError('ללקוח אין חובת דיווח מע"מ', "TAX_DEADLINE.VAT_NOT_APPLICABLE")

    year, month = _parse_period(period)
    offset = 2 if vat_type == VatType.BIMONTHLY else 1
    due_year, due_month = _filing_month(year, month, offset)
    return date(due_year, due_month, VAT_STATUTORY_DEADLINE_DAY)


def resolve_due_date(
    db: Session,
    client_record,
    deadline_type: DeadlineType,
    due_date: date | None,
    period: str | None,
) -> date:
    if deadline_type == DeadlineType.VAT:
        if period is None and due_date is not None:
            return due_date
        return resolve_vat_due_date(db, client_record, period)
    if due_date is None:
        raise AppError("יש להזין תאריך מועד", "TAX_DEADLINE.DUE_DATE_REQUIRED")
    return due_date
