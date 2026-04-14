from datetime import date
from decimal import Decimal
from typing import Optional

from app.annual_reports.models.annual_report_enums import AnnualReportStatus, ReportStage
from app.annual_reports.schemas.annual_report_responses import (
    AnnualReportDetailResponse,
    AnnualReportResponse,
    ScheduleEntryResponse,
    StatusHistoryResponse,
)
from app.core.exceptions import ConflictError
from .base import AnnualReportBaseService
from .messages import REPORT_AMEND_ONLY_SUBMITTED_ERROR


class AnnualReportQueryService(AnnualReportBaseService):
    def get_report(self, report_id: int) -> Optional[AnnualReportResponse]:
        report = self.repo.get_by_id(report_id)
        if not report:
            return None
        return self._to_responses([report])[0]

    def get_client_reports(self, client_id: int, page: int = 1, page_size: int = 20) -> tuple[list[AnnualReportResponse], int]:
        reports = self.repo.list_by_client(client_id, page=page, page_size=page_size)
        total = self.repo.count_by_client(client_id)
        return self._to_responses(reports), total

    def list_reports(
        self,
        tax_year: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "tax_year",
        order: str = "desc",
    ) -> tuple[list[AnnualReportResponse], int]:
        if tax_year is not None:
            items = self.repo.list_by_tax_year(tax_year, page=page, page_size=page_size, sort_by=sort_by, order=order)
            total = self.repo.count_by_tax_year(tax_year)
        else:
            items = self.repo.list_all(page=page, page_size=page_size, sort_by=sort_by, order=order)
            total = self.repo.count_all()
        return self._to_responses(items), total

    def get_season_summary(self, tax_year: int) -> dict:
        return self.repo.get_season_summary(tax_year)

    def get_overdue(self, tax_year: Optional[int] = None, page: int = 1, page_size: int = 20) -> list[AnnualReportResponse]:
        reports = self.repo.list_overdue(tax_year=tax_year, page=page, page_size=page_size)
        return self._to_responses(reports)

    def get_status_history(self, report_id: int) -> list:
        self._get_or_raise(report_id)
        return self.repo.get_status_history(report_id)

    def get_detail_report(self, report_id: int) -> Optional[AnnualReportDetailResponse]:
        """Return report with schedules, history, financial summary, and detail fields. None if not found."""
        from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
        from app.annual_reports.repositories.credit_point_repository import AnnualReportCreditPointRepository
        from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
        from app.annual_reports.repositories.detail_repository import AnnualReportDetailRepository

        report = self.get_report(report_id)
        if report is None:
            return None

        schedules = self.repo.get_schedules(report_id)
        history = self.repo.get_status_history(report_id)
        income_repo = AnnualReportIncomeRepository(self.db)
        expense_repo = AnnualReportExpenseRepository(self.db)
        total_income = income_repo.total_income(report_id)
        total_expenses = expense_repo.total_expenses(report_id)
        recognized_expenses = expense_repo.total_recognized_expenses(report_id)
        detail = AnnualReportDetailRepository(self.db).get_by_report_id(report_id)
        credit_breakdown = AnnualReportCreditPointRepository(self.db).aggregate_breakdown(report_id)

        response = AnnualReportDetailResponse(**report.model_dump())
        response.schedules = [ScheduleEntryResponse.model_validate(s) for s in schedules]
        response.status_history = [StatusHistoryResponse.model_validate(h) for h in history]
        response.total_income = total_income
        response.total_expenses = total_expenses
        response.taxable_income = total_income - recognized_expenses

        orm_report = self.repo.get_by_id(report_id)
        if detail:
            response.client_approved_at = detail.client_approved_at
            response.internal_notes = detail.internal_notes
            response.amendment_reason = detail.amendment_reason
        response.credit_points = credit_breakdown["credit_points"]
        response.pension_credit_points = credit_breakdown["pension_credit_points"]
        response.life_insurance_credit_points = credit_breakdown["life_insurance_credit_points"]
        response.tuition_credit_points = credit_breakdown["tuition_credit_points"]
        if orm_report:
            response.tax_refund_amount = float(orm_report.refund_due) if orm_report.refund_due is not None else None
            response.tax_due_amount = float(orm_report.tax_due) if orm_report.tax_due is not None else None

        from app.annual_reports.services.financial_service import AnnualReportFinancialService

        tax = AnnualReportFinancialService(self.db).get_tax_calculation(report_id)
        response.profit = tax.net_profit
        advances_paid = Decimal(str(self.advance_repo.sum_paid_by_client_year(orm_report.client_id, orm_report.tax_year)))
        response.final_balance = tax.tax_after_credits - advances_paid

        return response

    def amend_report(self, report_id: int, reason: str, actor_id: int, actor_name: str) -> AnnualReportDetailResponse:
        """Transition a SUBMITTED report to AMENDED and record the amendment reason."""
        from app.annual_reports.repositories.detail_repository import AnnualReportDetailRepository

        report = self._get_or_raise(report_id)
        if report.status != AnnualReportStatus.SUBMITTED:
            raise ConflictError(
                REPORT_AMEND_ONLY_SUBMITTED_ERROR.format(status=report.status.value),
                "ANNUAL_REPORT.INVALID_STATUS_FOR_AMEND",
            )

        self.transition_status(
            report_id=report_id,
            new_status=AnnualReportStatus.AMENDED.value,
            changed_by=actor_id,
            changed_by_name=actor_name,
            note=reason,
        )
        AnnualReportDetailRepository(self.db).update_meta(report_id, amendment_reason=reason)

        return self.get_detail_report(report_id)

    def kanban_view(self) -> list[dict]:
        """Group reports by stage for Kanban board."""
        from app.clients.repositories.client_repository import ClientRepository
        reports = self.repo.list_all_with_businesses()
        client_ids = {r.client_id for r in reports}
        clients = {c.id: c for c in ClientRepository(self.db).list_by_ids(list(client_ids))} if client_ids else {}

        stages = {stage.value: [] for stage in ReportStage}
        for report in reports:
            status_value = report.status.value if hasattr(report.status, "value") else report.status
            if status_value in ("not_started", "collecting_docs"):
                stage_key = ReportStage.MATERIAL_COLLECTION
            elif status_value == "docs_complete":
                stage_key = ReportStage.IN_PROGRESS
            elif status_value in ("in_preparation", "amended"):
                stage_key = ReportStage.FINAL_REVIEW
            elif status_value == "pending_client":
                stage_key = ReportStage.CLIENT_SIGNATURE
            elif status_value in ("assessment_issued", "objection_filed"):
                stage_key = ReportStage.POST_SUBMISSION
            else:  # submitted, accepted, closed
                stage_key = ReportStage.TRANSMITTED

            client = clients.get(report.client_id)
            stages[stage_key.value].append(
                {
                    "id": report.id,
                    "client_id": report.client_id,
                    "client_name": client.full_name if client else None,
                    "business_name": None,
                    "tax_year": report.tax_year,
                    "days_until_due": (
                        None if not report.filing_deadline
                        else (report.filing_deadline.date() - date.today()).days
                    ),
                }
            )

        return [{"stage": key, "reports": items} for key, items in stages.items()]
