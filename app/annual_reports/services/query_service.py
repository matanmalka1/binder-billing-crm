from typing import Optional

from app.annual_reports.models import AnnualReport
from app.annual_reports.models.annual_report_enums import ReportStage
from .base import AnnualReportBaseService


class AnnualReportQueryService(AnnualReportBaseService):
    def get_report(self, report_id: int) -> Optional[AnnualReport]:
        return self.repo.get_by_id(report_id)

    def get_client_reports(self, client_id: int) -> list[AnnualReport]:
        return self.repo.list_by_client(client_id)

    def list_reports(
        self,
        tax_year: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AnnualReport], int]:
        if tax_year is not None:
            items = self.repo.list_by_tax_year(tax_year, page=page, page_size=page_size)
            total = self.repo.count_by_tax_year(tax_year)
        else:
            items = self.repo.list_all(page=page, page_size=page_size)
            total = self.repo.count_all()
        return items, total

    def get_season_summary(self, tax_year: int) -> dict:
        return self.repo.get_season_summary(tax_year)

    def get_overdue(self, tax_year: Optional[int] = None) -> list[AnnualReport]:
        return self.repo.list_overdue(tax_year=tax_year)

    def get_status_history(self, report_id: int) -> list:
        self._get_or_raise(report_id)
        return self.repo.get_status_history(report_id)

    def kanban_view(self) -> list[dict]:
        """Group reports by stage for Kanban board."""
        records = self.repo.list_all_with_clients()
        stages = {stage.value: [] for stage in ReportStage}
        for report, client_name in records:
            stage_key = getattr(report, "status", None)
            # Map status to stage: simple mapping aligning with frontend STAGE_ORDER
            status_value = report.status.value if hasattr(report.status, "value") else report.status
            if status_value in ("not_started", "collecting_docs"):
                stage_key = ReportStage.MATERIAL_COLLECTION
            elif status_value in ("docs_complete", "in_preparation"):
                stage_key = ReportStage.IN_PROGRESS
            elif status_value == "pending_client":
                stage_key = ReportStage.CLIENT_SIGNATURE
            elif status_value == "submitted":
                stage_key = ReportStage.TRANSMITTED
            elif status_value in ("accepted", "assessment_issued", "closed"):
                stage_key = ReportStage.FINAL_REVIEW
            else:
                stage_key = ReportStage.MATERIAL_COLLECTION

            stages[stage_key.value].append(
                {
                    "id": report.id,
                    "client_id": report.client_id,
                    "client_name": client_name,
                    "tax_year": report.tax_year,
                    "days_until_due": None if not report.filing_deadline else (report.filing_deadline.date() - report.created_at.date()).days,
                }
            )

        return [
            {"stage": key, "reports": reports}
            for key, reports in stages.items()
        ]
