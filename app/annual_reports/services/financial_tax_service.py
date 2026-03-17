"""Tax and readiness operations for annual report financial service."""

from app.annual_reports.schemas.annual_report_financials import (
    BracketBreakdownItem,
    NationalInsuranceResponse,
    ReadinessCheckResponse,
    TaxCalculationResponse,
)
from app.annual_reports.services.ni_engine import calculate_national_insurance
from app.annual_reports.services.tax_engine import calculate_tax


class FinancialTaxMixin:
    def get_tax_calculation(self, report_id: int) -> TaxCalculationResponse:
        report = self._get_report_or_raise(report_id)
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

        tax = calculate_tax(summary.taxable_income, report.tax_year, credit_points, pension_deduction, donation_amount, other_credits)
        ni = calculate_national_insurance(summary.taxable_income, report.tax_year)
        net_profit = tax.taxable_income - tax.tax_after_credits
        vat_balance = self.vat_repo.sum_net_vat_by_client_year(report.client_id, report.tax_year)  # type: ignore[attr-defined]
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
                    issues.append(f"נספח נדרש לא הושלם: {label}")
            else:
                passed += 1
        else:
            passed += 1

        total_income = self.income_repo.total_income(report_id)
        if total_income == 0:
            issues.append("לא הוזנו נתוני הכנסה לדוח")
        else:
            passed += 1

        detail = self.detail_repo.get_by_report_id(report_id)
        if not detail or (detail.tax_due_amount is None and detail.tax_refund_amount is None):
            issues.append("חסר חישוב מס — יש למלא חוב מס או החזר מס")
        else:
            passed += 1

        if not detail or not detail.client_approved_at:
            issues.append("הדוח לא אושר על ידי הלקוח")
        else:
            passed += 1

        completion_pct = round(passed / 4 * 100, 1)
        return ReadinessCheckResponse(
            annual_report_id=report_id,
            is_ready=len(issues) == 0,
            issues=issues,
            completion_pct=completion_pct,
        )


__all__ = ["FinancialTaxMixin"]
