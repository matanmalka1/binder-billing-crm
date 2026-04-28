"""Lifecycle/season operations for AnnualReport entities."""

import datetime as _dt
from datetime import timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, case

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.models.annual_report_model import AnnualReport
from app.utils.time_utils import utcnow

DASHBOARD_FINAL_STATUSES = frozenset({
    AnnualReportStatus.SUBMITTED,
    AnnualReportStatus.ACCEPTED,
    AnnualReportStatus.CLOSED,
    AnnualReportStatus.CANCELED,
})


class AnnualReportLifecycleRepository:
    def list_overdue(self, tax_year: Optional[int] = None, page: int = 1, page_size: int = 20) -> list[AnnualReport]:
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
        q = q.order_by(AnnualReport.filing_deadline.asc())
        return self._paginate(q, page, page_size)

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

    def list_stuck_reports(self, stale_days: int = 7, limit: int = 3) -> list[AnnualReport]:
        """Return reports stuck in PENDING_CLIENT or COLLECTING_DOCS for >= stale_days."""
        cutoff = _dt.datetime.now(timezone.utc) - _dt.timedelta(days=stale_days)
        return (
            self.db.query(AnnualReport)
            .filter(
                AnnualReport.status.in_([
                    AnnualReportStatus.PENDING_CLIENT,
                    AnnualReportStatus.COLLECTING_DOCS,
                ]),
                AnnualReport.deleted_at.is_(None),
                AnnualReport.updated_at <= cutoff,
            )
            .order_by(AnnualReport.updated_at.asc())
            .limit(limit)
            .all()
        )

    def list_for_dashboard(self, limit: int = 50) -> list[AnnualReport]:
        """Return non-final reports with a filing_deadline set, ordered by deadline asc."""
        return (
            self.db.query(AnnualReport)
            .filter(
                AnnualReport.status.notin_(list(DASHBOARD_FINAL_STATUSES)),
                AnnualReport.filing_deadline.isnot(None),
                AnnualReport.deleted_at.is_(None),
            )
            .order_by(AnnualReport.filing_deadline.asc())
            .limit(limit)
            .all()
        )

    def get_season_summary(self, tax_year: int) -> dict:
        rows = (
            self.db.query(AnnualReport.status, func.count(AnnualReport.id).label("cnt"))
            .filter(AnnualReport.tax_year == tax_year, AnnualReport.deleted_at.is_(None))
            .group_by(AnnualReport.status)
            .all()
        )
        summary = {s.value: 0 for s in AnnualReportStatus}
        total = 0
        for row in rows:
            summary[row.status.value] += row.cnt
            total += row.cnt
        summary["total"] = total
        return summary


__all__ = ["AnnualReportLifecycleRepository"]
