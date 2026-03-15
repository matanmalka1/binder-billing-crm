"""Service for the annual report status report grouped by status."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models import AnnualReport, AnnualReportStatus
from app.clients.models.client import Client


class AnnualReportStatusReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_report(self, tax_year: int) -> dict:
        rows = (
            self.db.query(AnnualReport, Client.full_name)
            .join(Client, Client.id == AnnualReport.client_id)
            .filter(
                AnnualReport.tax_year == tax_year,
                AnnualReport.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
            .order_by(AnnualReport.filing_deadline.asc().nulls_last())
            .all()
        )

        today = date.today()
        grouped: dict[str, list] = {s.value: [] for s in AnnualReportStatus}

        for report, client_name in rows:
            days_until: Optional[int] = None
            if report.filing_deadline:
                dl = report.filing_deadline
                if hasattr(dl, "date"):
                    dl = dl.date()
                days_until = (dl - today).days

            filing_deadline_date = None
            if report.filing_deadline:
                filing_deadline_date = (
                    report.filing_deadline.date()
                    if hasattr(report.filing_deadline, "date")
                    else report.filing_deadline
                )

            grouped[report.status.value].append(
                {
                    "client_id": report.client_id,
                    "client_name": client_name,
                    "form_type": report.form_type.value if report.form_type else None,
                    "filing_deadline": filing_deadline_date,
                    "days_until_deadline": days_until,
                }
            )

        statuses = [
            {
                "status": status_value,
                "count": len(clients),
                "clients": clients,
            }
            for status_value, clients in grouped.items()
            if clients
        ]

        return {
            "tax_year": tax_year,
            "total": len(rows),
            "statuses": statuses,
        }
