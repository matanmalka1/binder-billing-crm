"""Service for income lines, expense lines, and financial summary."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
from app.annual_reports.schemas.annual_report_financials import (
    FinancialSummaryResponse,
    IncomeLineResponse,
    ExpenseLineResponse,
    ReadinessCheckResponse,
)
from app.annual_reports.services.tax_engine import calculate_tax, TaxCalculationResult


class AnnualReportFinancialService:
    def __init__(self, db: Session):
        self.db = db
        self.income_repo = AnnualReportIncomeRepository(db)
        self.expense_repo = AnnualReportExpenseRepository(db)
        self.report_repo = AnnualReportRepository(db)
        self.detail_repo = AnnualReportDetailRepository(db)

    def _get_report_or_raise(self, report_id: int):
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"הדוח השנתי {report_id} לא נמצא")
        return report

    # ── Income ────────────────────────────────────────────────────────────────

    def add_income(
        self,
        report_id: int,
        source_type: str,
        amount: Decimal,
        description: Optional[str] = None,
    ) -> IncomeLineResponse:
        self._get_report_or_raise(report_id)
        try:
            st = IncomeSourceType(source_type)
        except ValueError:
            valid = [e.value for e in IncomeSourceType]
            raise ValueError(f"סוג הכנסה לא חוקי '{source_type}'. חוקיים: {valid}")
        line = self.income_repo.add(report_id, st, amount, description)
        return IncomeLineResponse.model_validate(line)

    def update_income(
        self, report_id: int, line_id: int, **fields
    ) -> IncomeLineResponse:
        self._get_report_or_raise(report_id)
        if "source_type" in fields and fields["source_type"] is not None:
            try:
                fields["source_type"] = IncomeSourceType(fields["source_type"])
            except ValueError:
                valid = [e.value for e in IncomeSourceType]
                raise ValueError(f"סוג הכנסה לא חוקי. חוקיים: {valid}")
        line = self.income_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise ValueError(f"שורת הכנסה {line_id} לא נמצאה")
        return IncomeLineResponse.model_validate(line)

    def delete_income(self, report_id: int, line_id: int) -> None:
        self._get_report_or_raise(report_id)
        if not self.income_repo.delete(line_id):
            raise ValueError(f"שורת הכנסה {line_id} לא נמצאה")

    # ── Expenses ──────────────────────────────────────────────────────────────

    def add_expense(
        self,
        report_id: int,
        category: str,
        amount: Decimal,
        description: Optional[str] = None,
    ) -> ExpenseLineResponse:
        self._get_report_or_raise(report_id)
        try:
            cat = ExpenseCategoryType(category)
        except ValueError:
            valid = [e.value for e in ExpenseCategoryType]
            raise ValueError(f"קטגוריית הוצאה לא חוקית '{category}'. חוקיות: {valid}")
        line = self.expense_repo.add(report_id, cat, amount, description)
        return ExpenseLineResponse.model_validate(line)

    def update_expense(
        self, report_id: int, line_id: int, **fields
    ) -> ExpenseLineResponse:
        self._get_report_or_raise(report_id)
        if "category" in fields and fields["category"] is not None:
            try:
                fields["category"] = ExpenseCategoryType(fields["category"])
            except ValueError:
                valid = [e.value for e in ExpenseCategoryType]
                raise ValueError(f"קטגוריית הוצאה לא חוקית. חוקיות: {valid}")
        line = self.expense_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise ValueError(f"שורת הוצאה {line_id} לא נמצאה")
        return ExpenseLineResponse.model_validate(line)

    def delete_expense(self, report_id: int, line_id: int) -> None:
        self._get_report_or_raise(report_id)
        if not self.expense_repo.delete(line_id):
            raise ValueError(f"שורת הוצאה {line_id} לא נמצאה")

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_financial_summary(self, report_id: int) -> FinancialSummaryResponse:
        self._get_report_or_raise(report_id)
        income_lines = self.income_repo.list_by_report(report_id)
        expense_lines = self.expense_repo.list_by_report(report_id)
        total_income = self.income_repo.total_income(report_id)
        total_expenses = self.expense_repo.total_expenses(report_id)
        taxable_income = total_income - total_expenses
        return FinancialSummaryResponse(
            annual_report_id=report_id,
            total_income=float(total_income),
            total_expenses=float(total_expenses),
            taxable_income=float(taxable_income),
            income_lines=[IncomeLineResponse.model_validate(l) for l in income_lines],
            expense_lines=[ExpenseLineResponse.model_validate(l) for l in expense_lines],
        )

    # ── Tax calculation ───────────────────────────────────────────────────────

    def get_tax_calculation(self, report_id: int) -> TaxCalculationResult:
        summary = self.get_financial_summary(report_id)
        detail = self.detail_repo.get_by_report_id(report_id)
        credit_points = float(detail.credit_points) if (detail and detail.credit_points is not None) else 2.25
        return calculate_tax(summary.taxable_income, credit_points)

    # ── Readiness ─────────────────────────────────────────────────────────────

    # Hebrew labels for schedule keys
    _SCHEDULE_LABELS: dict[str, str] = {
        "schedule_b": "נספח ב — שכירות",
        "schedule_bet": "נספח בית — רווחי הון",
        "schedule_gimmel": 'נספח ג — הכנסות מחו"ל',
        "schedule_dalet": "נספח ד — פחת",
        "schedule_heh": "נספח ה — שכר דירה פטור",
    }

    def get_readiness_check(self, report_id: int) -> ReadinessCheckResponse:
        report = self._get_report_or_raise(report_id)
        issues: list[str] = []

        # Check required schedules complete
        schedules = self.report_repo.get_schedules(report_id)
        for s in schedules:
            if s.is_required and not s.is_complete:
                label = self._SCHEDULE_LABELS.get(s.schedule.value, s.schedule.value)
                issues.append(f"נספח נדרש לא הושלם: {label}")

        # Check income data present
        total_income = self.income_repo.total_income(report_id)
        if total_income == 0:
            issues.append("לא הוזנו נתוני הכנסה לדוח")

        # Check detail has tax result
        detail = self.detail_repo.get_by_report_id(report_id)
        if not detail or (detail.tax_due_amount is None and detail.tax_refund_amount is None):
            issues.append("חסר חישוב מס — יש למלא חוב מס או החזר מס")

        # Check client approval
        if not detail or not detail.client_approved_at:
            issues.append("הדוח לא אושר על ידי הלקוח")

        return ReadinessCheckResponse(
            annual_report_id=report_id,
            is_ready=len(issues) == 0,
            issues=issues,
        )


__all__ = ["AnnualReportFinancialService"]
