from sqlalchemy import String, case, func, select
from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_model import AnnualReport
from app.advance_payments.models.advance_payment import AdvancePayment
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import ObligationType
from app.common.repositories.base_repository import BaseRepository
from app.tax_calendar.models.tax_calendar_entry import TaxCalendarEntry
from app.vat_reports.models.vat_work_item import VatWorkItem


def _entry_sort_clauses():
    # periodic rows sort by their period; annual_report (period=NULL) sorts after
    # all months of the same tax_year using a synthetic '9999-99' sentinel.
    period_key = func.coalesce(
        TaxCalendarEntry.period,
        func.cast(TaxCalendarEntry.tax_year, String) + "-99",
    )
    obligation_priority = case(
        (TaxCalendarEntry.obligation_type == ObligationType.VAT, 1),
        (TaxCalendarEntry.obligation_type == ObligationType.ADVANCE_PAYMENT, 2),
        (TaxCalendarEntry.obligation_type == ObligationType.ANNUAL_REPORT, 3),
        else_=9,
    )
    frequency_priority = case(
        (TaxCalendarEntry.period_months_count == 1, 1),
        (TaxCalendarEntry.period_months_count == 2, 2),
        else_=9,
    )
    return (
        TaxCalendarEntry.tax_year.asc(),
        period_key.asc(),
        obligation_priority.asc(),
        frequency_priority.asc(),
        TaxCalendarEntry.due_date.asc(),
        TaxCalendarEntry.id.asc(),
    )


class TaxCalendarGroupedRepository(BaseRepository[TaxCalendarEntry]):
    def __init__(self, db: Session):
        self.db = db

    def list_entries(
        self,
        *,
        start_year: int | None,
        end_year: int | None,
        obligation_type: ObligationType | None,
    ) -> list[TaxCalendarEntry]:
        stmt = select(TaxCalendarEntry)
        if start_year is not None:
            stmt = stmt.where(TaxCalendarEntry.tax_year >= start_year)
        if end_year is not None:
            stmt = stmt.where(TaxCalendarEntry.tax_year <= end_year)
        if obligation_type is not None:
            stmt = stmt.where(TaxCalendarEntry.obligation_type == obligation_type)
        else:
            stmt = stmt.where(
                TaxCalendarEntry.obligation_type.in_(
                    [
                        ObligationType.VAT,
                        ObligationType.ADVANCE_PAYMENT,
                        ObligationType.ANNUAL_REPORT,
                    ]
                )
            )
        return self.db.scalars(stmt.order_by(*_entry_sort_clauses())).all()

    def list_vat_for_entries(self, entry_ids: list[int]) -> list[VatWorkItem]:
        if not entry_ids:
            return []
        return self.db.scalars(
            select(VatWorkItem)
            .where(VatWorkItem.tax_calendar_entry_id.in_(entry_ids))
            .where(VatWorkItem.deleted_at.is_(None))
        ).all()

    def list_advance_for_entries(self, entry_ids: list[int]) -> list[AdvancePayment]:
        if not entry_ids:
            return []
        return self.db.scalars(
            select(AdvancePayment)
            .where(AdvancePayment.tax_calendar_entry_id.in_(entry_ids))
            .where(AdvancePayment.deleted_at.is_(None))
        ).all()

    def list_annual_for_entries(self, entry_ids: list[int]) -> list[AnnualReport]:
        if not entry_ids:
            return []
        return self.db.scalars(
            select(AnnualReport)
            .where(AnnualReport.tax_calendar_entry_id.in_(entry_ids))
            .where(AnnualReport.deleted_at.is_(None))
        ).all()

    def get_entry(self, entry_id: int) -> TaxCalendarEntry | None:
        return self.db.get(TaxCalendarEntry, entry_id)

    def list_vat_items(self, entry_id: int):
        return self.db.execute(
            self._with_client(VatWorkItem).where(
                VatWorkItem.tax_calendar_entry_id == entry_id,
                VatWorkItem.deleted_at.is_(None),
            )
        ).all()

    def list_advance_items(self, entry_id: int):
        return self.db.execute(
            self._with_client(AdvancePayment).where(
                AdvancePayment.tax_calendar_entry_id == entry_id,
                AdvancePayment.deleted_at.is_(None),
            )
        ).all()

    def list_annual_items(self, entry_id: int):
        return self.db.execute(
            self._with_client(AnnualReport).where(
                AnnualReport.tax_calendar_entry_id == entry_id,
                AnnualReport.deleted_at.is_(None),
            )
        ).all()

    def _with_client(self, model):
        return (
            select(model, ClientRecord, LegalEntity)
            .join(ClientRecord, model.client_record_id == ClientRecord.id)
            .join(LegalEntity, ClientRecord.legal_entity_id == LegalEntity.id)
        )
