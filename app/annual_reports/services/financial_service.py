"""Service for income lines, expense lines, and financial summary."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
from app.annual_reports.schemas.annual_report_financials import (
    BracketBreakdownItem,
    FinancialSummaryResponse,
    IncomeLineResponse,
    ExpenseLineResponse,
    NationalInsuranceResponse,
    ReadinessCheckResponse,
    TaxCalculationResponse,
)
from app.annual_reports.services.tax_engine import (
    calculate_tax,
    TaxCalculationResult,
    calculate_national_insurance,
)
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus


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
            raise NotFoundError(f"הדוח השנתי {report_id} לא נמצא", "ANNUAL_REPORT.NOT_FOUND")
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
        valid_sources = {e.value for e in IncomeSourceType}
        if source_type not in valid_sources:
            raise AppError(
                f"סוג הכנסה לא חוקי '{source_type}'. חוקיים: {sorted(valid_sources)}",
                "ANNUAL_REPORT.INVALID_TYPE",
            )
        st = IncomeSourceType(source_type)
        line = self.income_repo.add(report_id, st, amount, description)
        return IncomeLineResponse.model_validate(line)

    def update_income(
        self, report_id: int, line_id: int, **fields
    ) -> IncomeLineResponse:
        self._get_report_or_raise(report_id)
        if "source_type" in fields and fields["source_type"] is not None:
            valid_sources = {e.value for e in IncomeSourceType}
            if fields["source_type"] not in valid_sources:
                raise AppError(f"סוג הכנסה לא חוקי. חוקיים: {sorted(valid_sources)}", "ANNUAL_REPORT.INVALID_TYPE")
            fields["source_type"] = IncomeSourceType(fields["source_type"])
        line = self.income_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(f"שורת הכנסה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")
        return IncomeLineResponse.model_validate(line)

    def delete_income(self, report_id: int, line_id: int) -> None:
        self._get_report_or_raise(report_id)
        if not self.income_repo.delete(line_id):
            raise NotFoundError(f"שורת הכנסה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")

    # ── Expenses ──────────────────────────────────────────────────────────────

    def add_expense(
        self,
        report_id: int,
        category: str,
        amount: Decimal,
        description: Optional[str] = None,
        recognition_rate: Optional[Decimal] = None,
        supporting_document_ref: Optional[str] = None,
        supporting_document_id: Optional[int] = None,
    ) -> ExpenseLineResponse:
        self._get_report_or_raise(report_id)
        valid_categories = {e.value for e in ExpenseCategoryType}
        if category not in valid_categories:
            raise AppError(
                f"קטגוריית הוצאה לא חוקית '{category}'. חוקיות: {sorted(valid_categories)}",
                "ANNUAL_REPORT.INVALID_TYPE",
            )
        cat = ExpenseCategoryType(category)
        line = self.expense_repo.add(
            report_id, cat, amount, description, recognition_rate,
            supporting_document_ref, supporting_document_id,
        )
        return ExpenseLineResponse.model_validate(line)

    def update_expense(
        self, report_id: int, line_id: int, **fields
    ) -> ExpenseLineResponse:
        self._get_report_or_raise(report_id)
        if "category" in fields and fields["category"] is not None:
            valid_categories = {e.value for e in ExpenseCategoryType}
            if fields["category"] not in valid_categories:
                raise AppError(f"קטגוריית הוצאה לא חוקית. חוקיות: {sorted(valid_categories)}", "ANNUAL_REPORT.INVALID_TYPE")
            fields["category"] = ExpenseCategoryType(fields["category"])
        line = self.expense_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(f"שורת הוצאה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")
        return ExpenseLineResponse.model_validate(line)

    def delete_expense(self, report_id: int, line_id: int) -> None:
        self._get_report_or_raise(report_id)
        if not self.expense_repo.delete(line_id):
            raise NotFoundError(f"שורת הוצאה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_financial_summary(self, report_id: int) -> FinancialSummaryResponse:
        self._get_report_or_raise(report_id)
        income_lines = self.income_repo.list_by_report(report_id)
        expense_lines = self.expense_repo.list_by_report(report_id)
        total_income = self.income_repo.total_income(report_id)
        gross_expenses = self.expense_repo.total_expenses(report_id)
        recognized_expenses = self.expense_repo.total_recognized_expenses(report_id)
        taxable_income = total_income - recognized_expenses
        return FinancialSummaryResponse(
            annual_report_id=report_id,
            total_income=float(total_income),
            gross_expenses=float(gross_expenses),
            recognized_expenses=float(recognized_expenses),
            taxable_income=float(taxable_income),
            income_lines=[IncomeLineResponse.model_validate(l) for l in income_lines],
            expense_lines=[ExpenseLineResponse.model_validate(l) for l in expense_lines],
        )

    # ── Tax calculation ───────────────────────────────────────────────────────

    def get_tax_calculation(self, report_id: int) -> TaxCalculationResponse:
        summary = self.get_financial_summary(report_id)
        detail = self.detail_repo.get_by_report_id(report_id)
        base_cp = float(detail.credit_points) if (detail and detail.credit_points is not None) else 2.25
        pension_cp = float(detail.pension_credit_points) if (detail and detail.pension_credit_points is not None) else 0.0
        life_ins_cp = float(detail.life_insurance_credit_points) if (detail and detail.life_insurance_credit_points is not None) else 0.0
        tuition_cp = float(detail.tuition_credit_points) if (detail and detail.tuition_credit_points is not None) else 0.0
        credit_points = base_cp + pension_cp + life_ins_cp + tuition_cp
        pension_deduction = float(detail.pension_contribution) if (detail and detail.pension_contribution is not None) else 0.0
        donation_amount = float(detail.donation_amount) if (detail and detail.donation_amount is not None) else 0.0
        other_credits = float(detail.other_credits) if (detail and detail.other_credits is not None) else 0.0
        tax = calculate_tax(summary.taxable_income, credit_points, pension_deduction, donation_amount, other_credits)
        ni = calculate_national_insurance(summary.taxable_income)
        net_profit = tax.taxable_income - tax.tax_after_credits

        report = self._get_report_or_raise(report_id)
        year_str = str(report.tax_year)
        vat_row = (
            self.db.query(sa_func.sum(VatWorkItem.net_vat).label("total_vat"))
            .filter(
                VatWorkItem.client_id == report.client_id,
                sa_func.substr(VatWorkItem.period, 1, 4) == year_str,
            )
            .one_or_none()
        )
        vat_balance = float(vat_row[0] or 0) if vat_row and vat_row[0] is not None else None

        advances_paid = sum(
            float(p.paid_amount)
            for p in self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.client_id == report.client_id,
                AdvancePayment.year == report.tax_year,
                AdvancePayment.status == AdvancePaymentStatus.PAID,
            )
            .all()
            if p.paid_amount is not None
        )

        total_liability = round(
            tax.tax_after_credits + ni.total + (vat_balance or 0) - advances_paid, 2
        )

        return TaxCalculationResponse(
            taxable_income=tax.taxable_income,
            pension_deduction=tax.pension_deduction,
            tax_before_credits=tax.tax_before_credits,
            credit_points_value=tax.credit_points_value,
            donation_credit=tax.donation_credit,
            other_credits=tax.other_credits,
            tax_after_credits=tax.tax_after_credits,
            net_profit=round(net_profit, 2),
            effective_rate=tax.effective_rate,
            national_insurance=NationalInsuranceResponse(
                base_amount=ni.base_amount,
                high_amount=ni.high_amount,
                total=ni.total,
            ),
            brackets=[
                BracketBreakdownItem(
                    rate=b.rate,
                    from_amount=b.from_amount,
                    to_amount=b.to_amount,
                    taxable_in_bracket=b.taxable_in_bracket,
                    tax_in_bracket=b.tax_in_bracket,
                )
                for b in tax.brackets
            ],
            total_liability=total_liability,
        )

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
        self._get_report_or_raise(report_id)
        issues: list[str] = []
        passed = 0

        # Check 1: required schedules complete (aggregate — counts as one check)
        schedules = self.report_repo.get_schedules(report_id)
        required = [s for s in schedules if s.is_required]
        if required:
            incomplete = [s for s in required if not s.is_complete]
            if incomplete:
                for s in incomplete:
                    label = self._SCHEDULE_LABELS.get(s.schedule.value, s.schedule.value)
                    issues.append(f"נספח נדרש לא הושלם: {label}")
            else:
                passed += 1
        else:
            passed += 1  # no required schedules → check passes

        # Check 2: income data present
        total_income = self.income_repo.total_income(report_id)
        if total_income == 0:
            issues.append("לא הוזנו נתוני הכנסה לדוח")
        else:
            passed += 1

        # Check 3: tax result filled
        detail = self.detail_repo.get_by_report_id(report_id)
        if not detail or (detail.tax_due_amount is None and detail.tax_refund_amount is None):
            issues.append("חסר חישוב מס — יש למלא חוב מס או החזר מס")
        else:
            passed += 1

        # Check 4: client approval
        if not detail or not detail.client_approved_at:
            issues.append("הדוח לא אושר על ידי הלקוח")
        else:
            passed += 1

        total_checks = 4
        completion_pct = round(passed / total_checks * 100, 1)

        return ReadinessCheckResponse(
            annual_report_id=report_id,
            is_ready=len(issues) == 0,
            issues=issues,
            completion_pct=completion_pct,
        )


__all__ = ["AnnualReportFinancialService"]
