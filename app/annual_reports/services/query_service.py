from datetime import date
from typing import Optional

from app.annual_reports.models.annual_report_enums import AnnualReportStatus, ReportStage
from app.annual_reports.schemas.annual_report_responses import AnnualReportDetailResponse, AnnualReportResponse, ScheduleEntryResponse, StatusHistoryResponse
from app.core.exceptions import ConflictError
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

    def get_overdue(self, tax_year: Optional[int] = None) -> list[AnnualReportResponse]:
        reports = self.repo.list_overdue(tax_year=tax_year)
        return self._to_responses(reports)

    def get_status_history(self, report_id: int) -> list:
        self._get_or_raise(report_id)
        return self.repo.get_status_history(report_id)

    def get_detail_report(self, report_id: int) -> Optional[AnnualReportDetailResponse]:
        """Return report with schedules, history, financial summary, and detail fields. None if not found."""
        from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
        from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
        from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
        report = self.get_report(report_id)
        if report is None:
            return None
        schedules = self.repo.get_schedules(report_id)
        history = self.repo.get_status_history(report_id)
        income_repo = AnnualReportIncomeRepository(self.db)
        expense_repo = AnnualReportExpenseRepository(self.db)
        total_income = income_repo.total_income(report_id)
        total_expenses = expense_repo.total_expenses(report_id)
        detail = AnnualReportDetailRepository(self.db).get_by_report_id(report_id)
        response = AnnualReportDetailResponse(**report.model_dump())
        response.schedules = [ScheduleEntryResponse.model_validate(s) for s in schedules]
        response.status_history = [StatusHistoryResponse.model_validate(h) for h in history]
        response.total_income = float(total_income)
        response.total_expenses = float(total_expenses)
        response.taxable_income = float(total_income - total_expenses)
        if detail:
            response.tax_refund_amount = float(detail.tax_refund_amount) if detail.tax_refund_amount is not None else None
            response.tax_due_amount = float(detail.tax_due_amount) if detail.tax_due_amount is not None else None
            response.client_approved_at = detail.client_approved_at
            response.internal_notes = detail.internal_notes
            response.amendment_reason = detail.amendment_reason
        try:
            from app.annual_reports.services.financial_service import AnnualReportFinancialService
            from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
            orm_report = self.repo.get_by_id(report_id)
            tax = AnnualReportFinancialService(self.db).get_tax_calculation(report_id)
            response.profit = tax.net_profit
            advances_paid = sum(
                float(p.paid_amount)
                for p in self.db.query(AdvancePayment).filter(
                    AdvancePayment.client_id == orm_report.client_id,
                    AdvancePayment.year == orm_report.tax_year,
                    AdvancePayment.status == AdvancePaymentStatus.PAID,
                ).all()
                if p.paid_amount is not None
            )
            response.final_balance = round(tax.tax_after_credits - advances_paid, 2)
        except Exception:
            pass
        return response

    def amend_report(self, report_id: int, reason: str, actor_id: int, actor_name: str) -> AnnualReportDetailResponse:
        """Transition a SUBMITTED report to AMENDED and record the amendment reason."""
        from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
        report = self._get_or_raise(report_id)
        if report.status != AnnualReportStatus.SUBMITTED:
            raise ConflictError(
                f"ניתן לתקן רק דוח בסטטוס 'הוגש'. הסטטוס הנוכחי: {report.status.value}",
                "ANNUAL_REPORT.INVALID_STATUS_FOR_AMEND",
            )
        self.repo.update(report_id, status=AnnualReportStatus.AMENDED)
        self.repo.append_status_history(
            annual_report_id=report_id,
            from_status=AnnualReportStatus.SUBMITTED,
            to_status=AnnualReportStatus.AMENDED,
            changed_by=actor_id,
            changed_by_name=actor_name,
            note=reason,
        )
        AnnualReportDetailRepository(self.db).upsert(report_id, amendment_reason=reason)
        # Cancel any pending signature requests created before submission (item 14)
        self._cancel_pending_signature_requests(report_id, actor_id, actor_name, "תיקון דוח — ביטול בקשת חתימה")
        return self.get_detail_report(report_id)

    def kanban_view(self) -> list[dict]:
        """Group reports by stage for Kanban board."""
        reports = self.repo.list_all_with_clients()
        client_ids = {r.client_id for r in reports}
        clients = self.client_repo.list_by_ids(list(client_ids)) if client_ids else []
        id_to_name = {c.id: c.full_name for c in clients}
        stages = {stage.value: [] for stage in ReportStage}
        for report in reports:
            stage_key = getattr(report, "status", None)
            # Map status to stage: simple mapping aligning with frontend STAGE_ORDER
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

            stages[stage_key.value].append(
                {
                    "id": report.id,
                    "client_id": report.client_id,
                    "client_name": id_to_name.get(report.client_id),
                    "tax_year": report.tax_year,
                    "days_until_due": None if not report.filing_deadline else (report.filing_deadline.date() - date.today()).days,
                }
            )

        return [{"stage": key, "reports": reports} for key, reports in stages.items()]
