from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ReportStage
from app.repositories.annual_report_repository import AnnualReportRepository
from app.repositories.client_repository import ClientRepository
from app.services.tax_deadline_service import TaxDeadlineService


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

        submitted = self.report_repo.count_by_stage(ReportStage.TRANSMITTED)

        in_progress = (
            self.report_repo.count_by_stage(ReportStage.IN_PROGRESS)
            + self.report_repo.count_by_stage(ReportStage.FINAL_REVIEW)
            + self.report_repo.count_by_stage(ReportStage.CLIENT_SIGNATURE)
        )

        material_collection = self.report_repo.count_by_stage(
            ReportStage.MATERIAL_COLLECTION
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