from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AnnualReport, ReportStage
from app.repositories.annual_report_repository import AnnualReportRepository
from app.repositories.client_repository import ClientRepository


class AnnualReportService:
    """Annual report lifecycle management business logic."""

    # Stage transition order
    STAGE_ORDER = [
        ReportStage.MATERIAL_COLLECTION,
        ReportStage.IN_PROGRESS,
        ReportStage.FINAL_REVIEW,
        ReportStage.CLIENT_SIGNATURE,
        ReportStage.TRANSMITTED,
    ]

    def __init__(self, db: Session):
        self.db = db
        self.report_repo = AnnualReportRepository(db)
        self.client_repo = ClientRepository(db)

    def create_report(
        self,
        client_id: int,
        tax_year: int,
        form_type: Optional[str] = None,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AnnualReport:
        """Create new annual report for client."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        existing = self.report_repo.get_by_client_year(client_id, tax_year)
        if existing:
            raise ValueError(
                f"Annual report for client {client_id} year {tax_year} already exists"
            )

        return self.report_repo.create(
            client_id=client_id,
            tax_year=tax_year,
            form_type=form_type,
            due_date=due_date,
            notes=notes,
        )

    def transition_stage(
        self,
        report_id: int,
        new_stage: ReportStage,
    ) -> AnnualReport:
        """Transition report to new stage."""
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        if report.stage == new_stage:
            return report

        self._validate_stage_transition(report.stage, new_stage)

        updated = self.report_repo.update(
            report_id,
            stage=new_stage,
            status=self._derive_status(new_stage),
        )
        return updated

    def mark_submitted(
        self,
        report_id: int,
        submitted_at: datetime,
    ) -> AnnualReport:
        """Mark report as submitted."""
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        if report.stage != ReportStage.TRANSMITTED:
            raise ValueError("Report must be in TRANSMITTED stage before marking submitted")

        return self.report_repo.update(
            report_id,
            submitted_at=submitted_at,
            status="completed",
        )

    def get_reports_by_stage(self, stage: ReportStage) -> list[AnnualReport]:
        """Get all reports at specific stage."""
        return self.report_repo.list_by_stage(stage)

    def get_client_reports(
        self,
        client_id: int,
        tax_year: Optional[int] = None,
    ) -> list[AnnualReport]:
        """Get reports for client."""
        return self.report_repo.list_by_client(client_id, tax_year)

    def _validate_stage_transition(
        self,
        current_stage: ReportStage,
        new_stage: ReportStage,
    ) -> None:
        """Validate stage transition is allowed."""
        # Lock transmitted reports (aligns with "submitted reports cannot be edited")
        if current_stage == ReportStage.TRANSMITTED and new_stage != current_stage:
            raise ValueError("Cannot change stage after transmission")

        current_idx = self.STAGE_ORDER.index(current_stage)
        new_idx = self.STAGE_ORDER.index(new_stage)

        # Allow moving one step forward or backward; disallow skips
        if abs(new_idx - current_idx) > 1:
            raise ValueError(f"Cannot skip stages from {current_stage} to {new_stage}")

    def _derive_status(self, stage: ReportStage) -> str:
        """Derive status from stage."""
        if stage == ReportStage.MATERIAL_COLLECTION:
            return "not_started"
        elif stage == ReportStage.TRANSMITTED:
            return "submitted"
        else:
            return "in_progress"
