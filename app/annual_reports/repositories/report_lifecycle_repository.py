"""Lifecycle/season operations for AnnualReport entities."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import func

from app.annual_reports.models import AnnualReport, AnnualReportStatus
from app.utils.time_utils import utcnow


class AnnualReportLifecycleRepository:
    def list_overdue(self, tax_year: Optional[int] = None) -> list[AnnualReport]:
        now = utcnow()
        open_statuses = [
            AnnualReportStatus.NOT_STARTED,
            AnnualReportStatus.COLLECTING_DOCS,
            AnnualReportStatus.DOCS_COMPLETE,
            AnnualReportStatus.IN_PREPARATION,
            AnnualReportStatus.PENDING_CLIENT,
        ]
        q = (
            self.db.query(AnnualReport)
            .filter(
                AnnualReport.status.in_(open_statuses),
                AnnualReport.filing_deadline < now,
                AnnualReport.filing_deadline.isnot(None),
                AnnualReport.deleted_at.is_(None),
            )
        )
        if tax_year:
            q = q.filter(AnnualReport.tax_year == tax_year)
        return q.order_by(AnnualReport.filing_deadline.asc()).all()

    def soft_delete(self, report_id: int, deleted_by: int) -> bool:
        report = self.db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
        if not report:
            return False
        report.deleted_at = utcnow()
        report.deleted_by = deleted_by
        self.db.commit()
        return True

    def sum_financials_by_year(self, tax_year: int) -> dict:
        row = (
            self.db.query(
                func.coalesce(func.sum(AnnualReport.refund_due), 0).label("total_refund_due"),
                func.coalesce(func.sum(AnnualReport.tax_due), 0).label("total_tax_due"),
            )
            .filter(AnnualReport.tax_year == tax_year, AnnualReport.deleted_at.is_(None))
            .one()
        )
        return {
            "total_refund_due": Decimal(str(row.total_refund_due)),
            "total_tax_due": Decimal(str(row.total_tax_due)),
        }

    def get_season_summary(self, tax_year: int) -> dict:
        all_reports = (
            self.db.query(AnnualReport)
            .filter(AnnualReport.tax_year == tax_year, AnnualReport.deleted_at.is_(None))
            .all()
        )
        summary = {s.value: 0 for s in AnnualReportStatus}
        for report in all_reports:
            summary[report.status.value] += 1
        summary["total"] = len(all_reports)
        return summary


__all__ = ["AnnualReportLifecycleRepository"]
