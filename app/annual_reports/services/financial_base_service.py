"""Shared base for annual report financial services."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.annual_reports.repositories.detail_repository import AnnualReportDetailRepository
from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.annual_reports.services.labels import SCHEDULE_LABELS


class FinancialBaseService:
    _SCHEDULE_LABELS = SCHEDULE_LABELS

    def __init__(self, db: Session):
        self.db = db
        self.income_repo = AnnualReportIncomeRepository(db)
        self.expense_repo = AnnualReportExpenseRepository(db)
        self.report_repo = AnnualReportRepository(db)
        self.detail_repo = AnnualReportDetailRepository(db)
        self.vat_repo = VatWorkItemRepository(db)
        self.advance_repo = AdvancePaymentRepository(db)
        self.business_repo = BusinessRepository(db)

    def _get_report_or_raise(self, report_id: int):
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(f"הדוח השנתי {report_id} לא נמצא", "ANNUAL_REPORT.NOT_FOUND")
        return report


__all__ = ["FinancialBaseService"]
