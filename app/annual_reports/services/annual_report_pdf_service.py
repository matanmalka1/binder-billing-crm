"""Annual report PDF export — thin service wrapper."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.annual_reports.services.financial_service import AnnualReportFinancialService
from app.annual_reports.services.detail_service import AnnualReportDetailService
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.annual_reports.services.annual_report_pdf_builder import build_pdf


class AnnualReportPdfService:
    def __init__(self, db: Session):
        self.db = db

    def generate(self, report_id: int) -> tuple[bytes, int]:
        repo = AnnualReportRepository(self.db)
        report = repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(f"דוח שנתי {report_id} לא נמצא", "ANNUAL_REPORT.NOT_FOUND")

        business = BusinessRepository(self.db).get_by_id(report.business_id)
        client_name = business.full_name if business else f"עסק #{report.business_id}"

        fin_svc = AnnualReportFinancialService(self.db)
        summary = fin_svc.get_financial_summary(report_id)
        tax = fin_svc.get_tax_calculation(report_id)

        detail_svc = AnnualReportDetailService(self.db)
        detail = detail_svc.get_detail(report_id)

        return build_pdf(report, client_name, summary, tax, detail), report.tax_year


__all__ = ["AnnualReportPdfService"]
