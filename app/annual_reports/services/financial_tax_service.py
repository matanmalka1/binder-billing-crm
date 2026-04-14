"""Tax and readiness operations for annual report financial service."""

from decimal import Decimal
from typing import Optional

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.schemas.annual_report_financials import (
    BracketBreakdownItem,
    NationalInsuranceResponse,
    ReadinessCheckResponse,
    TaxCalculationResponse,
    TaxCalculationSaveResponse,
)
from app.annual_reports.services.messages import (
    CLIENT_NOT_APPROVED_REPORT_ISSUE,
    INCOMPLETE_REQUIRED_SCHEDULE_ISSUE,
    MISSING_REPORT_INCOME_ISSUE,
    MISSING_TAX_CALCULATION_ISSUE,
    TAX_CONFLICT_ERROR,
)
from app.annual_reports.services.ni_engine import calculate_national_insurance
from app.annual_reports.services.tax_engine import calculate_tax
from app.core.exceptions import AppError

_PRE_SUBMISSION_STATUSES = {
    AnnualReportStatus.NOT_STARTED,
    AnnualReportStatus.COLLECTING_DOCS,
    AnnualReportStatus.DOCS_COMPLETE,
    AnnualReportStatus.IN_PREPARATION,
    AnnualReportStatus.PENDING_CLIENT,
}


class FinancialTaxMixin:
    def get_tax_calculation(self, report_id: int) -> TaxCalculationResponse:
        report = self._get_report_or_raise(report_id)
        summary = self.get_financial_summary(report_id)
        detail = self.detail_repo.get_by_report_id(report_id)
        credit_points = float(self.credit_point_repo.total_points_by_report_id(report_id))
        pension_deduction = float(detail.pension_contribution) if (detail and detail.pension_contribution is not None) else 0.0
        donation_amount = float(detail.donation_amount) if (detail and detail.donation_amount is not None) else 0.0
        other_credits = float(detail.other_credits) if (detail and detail.other_credits is not None) else 0.0

        tax = calculate_tax(summary.taxable_income, report.tax_year, credit_points, pension_deduction, donation_amount, other_credits)
        ni = calculate_national_insurance(summary.taxable_income, report.tax_year, report.client_type)
        net_profit = tax.taxable_income - tax.tax_after_credits
        vat_balance = self.vat_repo.sum_net_vat_by_client_year(report.client_id, report.tax_year)
        advances_paid = self.advance_repo.sum_paid_by_client_year(report.client_id, report.tax_year)  # type: ignore[attr-defined]

        total_liability = round(tax.tax_after_credits + ni.total + (vat_balance or 0) - advances_paid, 2)
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
            total_credit_points=tax.total_credit_points,
        )

    def get_readiness_check(self, report_id: int) -> ReadinessCheckResponse:
        self._get_report_or_raise(report_id)
        issues: list[str] = []
        passed = 0

        schedules = self.report_repo.get_schedules(report_id)
        required = [s for s in schedules if s.is_required]
        if required:
            incomplete = [s for s in required if not s.is_complete]
            if incomplete:
                for schedule in incomplete:
                    label = self._SCHEDULE_LABELS.get(schedule.schedule.value, schedule.schedule.value)
                    issues.append(INCOMPLETE_REQUIRED_SCHEDULE_ISSUE.format(label=label))
            else:
                passed += 1
        else:
            passed += 1

        total_income = self.income_repo.total_income(report_id)
        if total_income == 0:
            issues.append(MISSING_REPORT_INCOME_ISSUE)
        else:
            passed += 1

        detail = self.detail_repo.get_by_report_id(report_id)
        report = self._get_report_or_raise(report_id)
        if report.tax_due is None and report.refund_due is None:
            issues.append(MISSING_TAX_CALCULATION_ISSUE)
        else:
            passed += 1

        if not detail or not detail.client_approved_at:
            issues.append(CLIENT_NOT_APPROVED_REPORT_ISSUE)
        else:
            passed += 1

        completion_pct = round(passed / 4 * 100, 1)
        return ReadinessCheckResponse(
            annual_report_id=report_id,
            is_ready=len(issues) == 0,
            issues=issues,
            completion_pct=completion_pct,
        )


    def save_tax_calculation(
        self,
        report_id: int,
        tax_due: Optional[Decimal],
        refund_due: Optional[Decimal],
    ) -> TaxCalculationSaveResponse:
        """Persist computed tax_due / refund_due to the annual report record."""
        if tax_due is not None and refund_due is not None:
            raise AppError(
                TAX_CONFLICT_ERROR,
                "ANNUAL_REPORT.TAX_CONFLICT",
            )
        report = self._get_report_or_raise(report_id)
        updated = self.report_repo.update(report.id, tax_due=tax_due, refund_due=refund_due)
        return TaxCalculationSaveResponse(
            annual_report_id=report_id,
            tax_due=updated.tax_due,
            refund_due=updated.refund_due,
            saved_at=updated.updated_at,
        )

    def invalidate_tax_if_open(self, client_id: int, tax_year: int) -> None:
        """Clear saved tax_due / refund_due when advances change before submission.

        Called from the advance_payments API after a payment is marked PAID so
        the advisor is prompted to re-save the tax calculation.
        """
        report = self.report_repo.get_by_client_year(client_id, tax_year)
        if report and report.status in _PRE_SUBMISSION_STATUSES:
            self.report_repo.update(report.id, tax_due=None, refund_due=None)


__all__ = ["FinancialTaxMixin"]
