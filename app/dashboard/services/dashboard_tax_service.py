from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.repositories import AnnualReportRepository
from app.clients.repositories.client_repository import ClientRepository
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService


class DashboardTaxService:
    """Tax-specific dashboard widget data."""

    def __init__(self, db: Session):
        self.db = db
        self.report_repo = AnnualReportRepository(db)
        self.client_repo = ClientRepository(db)
        self.deadline_service = TaxDeadlineService(db)

    def get_submission_widget_data(
        self,
        tax_year: Optional[int] = None,
    ) -> dict:
        """Get annual report submission statistics."""
        if tax_year is None:
            tax_year = date.today().year

        total_clients = self.client_repo.count()

        # TRANSMITTED / fully done statuses
        submitted = (
            self.report_repo.count_by_status(AnnualReportStatus.SUBMITTED, tax_year=tax_year)
            + self.report_repo.count_by_status(AnnualReportStatus.ACCEPTED, tax_year=tax_year)
            + self.report_repo.count_by_status(AnnualReportStatus.CLOSED, tax_year=tax_year)
        )

        # IN_PROGRESS statuses
        in_progress = (
            self.report_repo.count_by_status(AnnualReportStatus.IN_PREPARATION, tax_year=tax_year)
            + self.report_repo.count_by_status(AnnualReportStatus.PENDING_CLIENT, tax_year=tax_year)
            + self.report_repo.count_by_status(AnnualReportStatus.ASSESSMENT_ISSUED, tax_year=tax_year)
            + self.report_repo.count_by_status(AnnualReportStatus.OBJECTION_FILED, tax_year=tax_year)
        )

        # MATERIAL_COLLECTION statuses
        material_collection = (
            self.report_repo.count_by_status(AnnualReportStatus.COLLECTING_DOCS, tax_year=tax_year)
            + self.report_repo.count_by_status(AnnualReportStatus.DOCS_COMPLETE, tax_year=tax_year)
        )

        not_started = total_clients - (submitted + in_progress + material_collection)

        submission_percentage = (
            round((submitted / total_clients) * 100, 1) if total_clients > 0 else 0.0
        )

        return {
            "tax_year": tax_year,
            "total_clients": total_clients,
            "reports_submitted": submitted,
            "reports_in_progress": in_progress,
            "reports_not_started": not_started,
            "submission_percentage": submission_percentage,
        }

    def get_deadline_summary(
        self,
        reference_date: Optional[date] = None,
    ) -> dict:
        """Get deadline summary for dashboard."""
        return self.deadline_service.get_urgent_deadlines_summary(reference_date)