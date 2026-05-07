from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_model import AnnualReport
from app.advance_payments.models.advance_payment import AdvancePayment
from app.common.enums import ObligationType
from app.tax_calendar.models.tax_calendar_entry import TaxCalendarEntry
from app.vat_reports.models.vat_work_item import VatWorkItem


class TaxCalendarGroupedRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_entries(
        self,
        *,
        start_year: int | None,
        end_year: int | None,
        obligation_type: ObligationType | None,
    ) -> list[TaxCalendarEntry]:
        query = self.db.query(TaxCalendarEntry)
        if start_year is not None:
            query = query.filter(TaxCalendarEntry.tax_year >= start_year)
        if end_year is not None:
            query = query.filter(TaxCalendarEntry.tax_year <= end_year)
        if obligation_type is not None:
            query = query.filter(TaxCalendarEntry.obligation_type == obligation_type)
        else:
            query = query.filter(
                TaxCalendarEntry.obligation_type.in_(
                    [
                        ObligationType.VAT,
                        ObligationType.ADVANCE_PAYMENT,
                        ObligationType.ANNUAL_REPORT,
                    ]
                )
            )
        return (
            query.order_by(
                TaxCalendarEntry.tax_year.asc(),
                TaxCalendarEntry.due_date.asc(),
                TaxCalendarEntry.obligation_type.asc(),
                TaxCalendarEntry.period.asc(),
            )
            .all()
        )

    def list_vat_for_entries(self, entry_ids: list[int]) -> list[VatWorkItem]:
        if not entry_ids:
            return []
        return (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.tax_calendar_entry_id.in_(entry_ids))
            .filter(VatWorkItem.deleted_at.is_(None))
            .all()
        )

    def list_advance_for_entries(self, entry_ids: list[int]) -> list[AdvancePayment]:
        if not entry_ids:
            return []
        return (
            self.db.query(AdvancePayment)
            .filter(AdvancePayment.tax_calendar_entry_id.in_(entry_ids))
            .filter(AdvancePayment.deleted_at.is_(None))
            .all()
        )

    def list_annual_for_entries(self, entry_ids: list[int]) -> list[AnnualReport]:
        if not entry_ids:
            return []
        return (
            self.db.query(AnnualReport)
            .filter(AnnualReport.tax_calendar_entry_id.in_(entry_ids))
            .filter(AnnualReport.deleted_at.is_(None))
            .all()
        )
