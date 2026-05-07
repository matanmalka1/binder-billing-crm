from datetime import date

from sqlalchemy.orm import Session

from app.common.enums import ObligationType
from app.core.exceptions import NotFoundError
from app.tax_calendar.repositories.grouped_repository import TaxCalendarGroupedRepository
from app.tax_calendar.schemas.grouped import (
    TaxCalendarGroupItem,
    TaxCalendarGroupItemsResponse,
)
from app.tax_calendar.services.grouped_service import _is_done, _row_due_date


def get_group_items(
    db: Session,
    tax_calendar_entry_id: int,
) -> TaxCalendarGroupItemsResponse:
    repo = TaxCalendarGroupedRepository(db)
    entry = repo.get_entry(tax_calendar_entry_id)
    if entry is None:
        raise NotFoundError("רשומת יומן מס לא נמצאה", "TAX_CALENDAR.NOT_FOUND")

    rows = _rows_for_entry(repo, entry)
    today = date.today()
    items = [
        _to_item(
            source_type=source_type,
            entry=entry,
            row=row,
            client=client,
            client_name=legal_entity.official_name,
            today=today,
        )
        for source_type, row, client, legal_entity in rows
    ]

    return TaxCalendarGroupItemsResponse(
        tax_calendar_entry_id=entry.id,
        obligation_type=entry.obligation_type.value,
        items=items,
    )


def _rows_for_entry(repo: TaxCalendarGroupedRepository, entry):
    if entry.obligation_type == ObligationType.VAT:
        return [("vat_work_item", *row) for row in repo.list_vat_items(entry.id)]
    if entry.obligation_type == ObligationType.ADVANCE_PAYMENT:
        return [("advance_payment", *row) for row in repo.list_advance_items(entry.id)]
    if entry.obligation_type == ObligationType.ANNUAL_REPORT:
        return [("annual_report", *row) for row in repo.list_annual_items(entry.id)]
    return []


def _to_item(
    *,
    source_type: str,
    entry,
    row,
    client,
    client_name: str | None,
    today: date,
) -> TaxCalendarGroupItem:
    effective_due_date = _row_due_date(entry.obligation_type, row, entry.due_date)
    done = _is_done(entry.obligation_type, row)
    return TaxCalendarGroupItem(
        source_type=source_type,
        source_id=row.id,
        client_record_id=row.client_record_id,
        office_client_number=client.office_client_number,
        client_name=client_name,
        period=getattr(row, "period", None),
        period_months_count=getattr(row, "period_months_count", None),
        tax_year=getattr(row, "tax_year", None),
        status=_status_value(row.status),
        regulatory_due_date=entry.due_date,
        effective_due_date=effective_due_date,
        done=done,
        overdue=not done and effective_due_date < today,
    )


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status)
