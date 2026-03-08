from datetime import date
from typing import Optional

from app.annual_reports.models import AnnualReport
from app.annual_reports.models.annual_report_enums import ReportStage
from app.annual_reports.schemas.annual_report import AnnualReportDetailResponse, AnnualReportResponse, ScheduleEntryResponse, StatusHistoryResponse
from .base import AnnualReportBaseService


class AnnualReportQueryService(AnnualReportBaseService):

    def get_report(self, report_id: int) -> Optional[AnnualReportResponse]:
        report = self.repo.get_by_id(report_id)
        if not report:
            return None
        return self._to_responses([report])[0]

    def get_client_reports(self, client_id: int) -> list[AnnualReportResponse]:
        reports = self.repo.list_by_client(client_id)
        return self._to_responses(reports)

    def list_reports(
        self,
        tax_year: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AnnualReportResponse], int]:
        if tax_year is not None:
            items = self.repo.list_by_tax_year(tax_year, page=page, page_size=page_size)
            total = self.repo.count_by_tax_year(tax_year)
        else:
            items = self.repo.list_all(page=page, page_size=page_size)
            total = self.repo.count_all()
        return self._to_responses(items), total

    def get_season_summary(self, tax_year: int) -> dict:
        return self.repo.get_season_summary(tax_year)

    def get_overdue(self, tax_year: Optional[int] = None) -> list[AnnualReportResponse]:
        reports = self.repo.list_overdue(tax_year=tax_year)
        return self._to_responses(reports)

    def get_status_history(self, report_id: int) -> list:
        self._get_or_raise(report_id)
        return self.repo.get_status_history(report_id)

    def get_detail_report(self, report_id: int) -> Optional[AnnualReportDetailResponse]:
        """Return report with schedules, history, and financial summary. None if not found."""
        from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
        from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
        report = self.get_report(report_id)
        if report is None:
            return None
        schedules = self.repo.get_schedules(report_id)
        history = self.repo.get_status_history(report_id)
        income_repo = AnnualReportIncomeRepository(self.db)
        expense_repo = AnnualReportExpenseRepository(self.db)
        total_income = income_repo.total_income(report_id)
        total_expenses = expense_repo.total_expenses(report_id)
        response = AnnualReportDetailResponse(**report.model_dump())
        response.schedules = [ScheduleEntryResponse.model_validate(s) for s in schedules]
        response.status_history = [StatusHistoryResponse.model_validate(h) for h in history]
        response.total_income = float(total_income)
        response.total_expenses = float(total_expenses)
        response.taxable_income = float(total_income - total_expenses)
        return response

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
            elif status_value == "docs_complete":
                stage_key = ReportStage.IN_PROGRESS
            elif status_value == "in_preparation":
                stage_key = ReportStage.FINAL_REVIEW
            elif status_value == "pending_client":
                stage_key = ReportStage.CLIENT_SIGNATURE
            else:  # submitted, accepted, assessment_issued, objection_filed, closed
                stage_key = ReportStage.TRANSMITTED

            stages[stage_key.value].append(
                {
                    "id": report.id,
                    "client_id": report.client_id,
                    "client_name": client_name,
                    "tax_year": report.tax_year,
                    "days_until_due": None if not report.filing_deadline else (report.filing_deadline.date() - date.today()).days,
                }
            )

        return [
            {"stage": key, "reports": reports}
            for key, reports in stages.items()
        ]
