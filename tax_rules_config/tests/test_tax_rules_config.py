"""
בדיקות קריטיות לתקינות הקונפיג.
מטרה: לוודא שלא נוצרות חובות שגויות ושכל ה-lookups עובדים.
"""
from __future__ import annotations

import pytest

from app.tax_rules.registry import (
    get_annual_report_rule,
    get_btl_due_day,
    get_effective_periodic_date,
    get_financial,
    get_financials,
    get_ni_brackets,
    get_obligations,
    get_periodic_calendar,
    get_vat_deduction_rate,
    validate,
)
from app.tax_rules.types import ObligationKind


# ── Helpers ────────────────────────────────────────────────────────────────────

def _profile(**kwargs):
    base = {
        "entity_type": "osek_murshe",
        "vat_reporting_frequency": "monthly",
        "income_tax_advance_frequency": "monthly",
        "income_tax_advance_rate": 10,
        "btl_status": "self_employed",
        "btl_advance_amount": 1000,
        "has_employees": False,
        "has_withholding_file": False,
        "requires_pcn874": False,
        "has_representative": False,
    }
    base.update(kwargs)
    return base


def _obligation_kinds(profile) -> set:
    return {r.kind for r in get_obligations(profile)}


# ── Validations ────────────────────────────────────────────────────────────────

class TestValidations:
    def test_osek_patur_no_periodic_vat(self):
        errors = validate(_profile(entity_type="osek_patur", vat_reporting_frequency="monthly"))
        assert any("עוסק פטור" in e for e in errors)

    def test_osek_patur_exempt_vat_ok(self):
        errors = validate(_profile(
            entity_type="osek_patur",
            vat_reporting_frequency="exempt",
            btl_status="self_employed",
        ))
        assert not errors

    def test_company_no_self_employed_ni(self):
        errors = validate(_profile(entity_type="company_ltd", btl_status="self_employed"))
        assert any("חברה" in e for e in errors)

    def test_advance_without_rate(self):
        errors = validate(_profile(income_tax_advance_frequency="monthly", income_tax_advance_rate=None))
        assert any("income_tax_advance_rate" in e for e in errors)

    def test_employee_no_vat(self):
        errors = validate(_profile(entity_type="employee", vat_reporting_frequency="monthly"))
        assert any("שכיר" in e for e in errors)

    def test_btl_self_employed_no_advance_amount(self):
        errors = validate(_profile(btl_status="self_employed", btl_advance_amount=None))
        assert any("btl_advance_amount" in e for e in errors)

    def test_valid_full_profile_no_errors(self):
        errors = validate(_profile())
        assert not errors


# ── Obligation resolution ──────────────────────────────────────────────────────

class TestObligationResolution:
    def test_osek_patur_gets_annual_vat_declaration(self):
        kinds = _obligation_kinds(_profile(
            entity_type="osek_patur",
            vat_reporting_frequency="exempt",
        ))
        assert ObligationKind.VAT_EXEMPT_ANNUAL_DECLARATION in kinds

    def test_osek_patur_no_periodic_vat_obligation(self):
        kinds = _obligation_kinds(_profile(
            entity_type="osek_patur",
            vat_reporting_frequency="exempt",
        ))
        assert ObligationKind.VAT_PERIODIC_REPORT not in kinds

    def test_osek_patur_can_have_income_tax_advances(self):
        kinds = _obligation_kinds(_profile(
            entity_type="osek_patur",
            vat_reporting_frequency="exempt",
            income_tax_advance_frequency="monthly",
        ))
        assert ObligationKind.INCOME_TAX_ADVANCE in kinds

    def test_pcn874_only_when_flagged(self):
        without = _obligation_kinds(_profile(requires_pcn874=False))
        with_flag = _obligation_kinds(_profile(requires_pcn874=True))
        assert ObligationKind.VAT_DETAILED_REPORT_PCN874 not in without
        assert ObligationKind.VAT_DETAILED_REPORT_PCN874 in with_flag

    def test_employer_102_only_with_employees(self):
        without = _obligation_kinds(_profile(has_employees=False))
        with_emp = _obligation_kinds(_profile(has_employees=True))
        assert ObligationKind.NATIONAL_INSURANCE_EMPLOYER_102 not in without
        assert ObligationKind.NATIONAL_INSURANCE_EMPLOYER_102 in with_emp

    def test_withholding_102_only_with_file(self):
        without = _obligation_kinds(_profile(has_withholding_file=False))
        with_file = _obligation_kinds(_profile(has_withholding_file=True))
        assert ObligationKind.WITHHOLDING_MONTHLY_102 not in without
        assert ObligationKind.WITHHOLDING_MONTHLY_102 in with_file

    def test_company_not_self_employed_ni(self):
        rules = get_obligations(_profile(
            entity_type="company_ltd",
            btl_status="not_self_employed",
            vat_reporting_frequency="monthly",
        ))
        ni_self = [
            r for r in rules
            if r.kind == ObligationKind.NATIONAL_INSURANCE_SELF_EMPLOYED_ADVANCE
            and r.not_applicable_reason_he
        ]
        assert ni_self


# ── Financials ─────────────────────────────────────────────────────────────────

class TestFinancials:
    def test_vat_rate_2026(self):
        c = get_financial(2026, "vat_rate_percent")
        assert c.value == 18.0

    def test_osek_patur_ceiling_2026(self):
        c = get_financial(2026, "osek_patur_ceiling_ils")
        assert c.value == 122_833

    def test_osek_patur_ceiling_2025_lower_than_2026(self):
        c25 = get_financial(2025, "osek_patur_ceiling_ils")
        c26 = get_financial(2026, "osek_patur_ceiling_ils")
        assert c25.value < c26.value

    def test_ni_brackets_2026_two_tiers(self):
        brackets = get_ni_brackets(2026)
        assert len(brackets) == 2
        assert brackets[0].rate_percent < brackets[1].rate_percent

    def test_missing_year_raises(self):
        with pytest.raises(KeyError):
            get_financials(1900)


# ── Calendar & overrides ───────────────────────────────────────────────────────

class TestCalendar:
    def test_all_12_periods_present(self):
        cal = get_periodic_calendar(2026)
        assert len(cal) == 12

    def test_feb_2026_override_applied(self):
        date = get_effective_periodic_date(2026, "2026-02", "effective_vat_periodic_and_income_tax_advances")
        assert date == "2026-03-26"

    def test_jan_2026_no_override(self):
        date = get_effective_periodic_date(2026, "2026-01", "effective_vat_periodic_and_income_tax_advances")
        assert date == "2026-02-16"

    def test_missing_year_raises(self):
        with pytest.raises(KeyError):
            get_periodic_calendar(1900)

    def test_btl_due_day_is_15(self):
        assert get_btl_due_day() == 15


# ── VAT deduction ──────────────────────────────────────────────────────────────

class TestVatDeduction:
    def test_entertainment_zero(self):
        assert get_vat_deduction_rate("entertainment") == 0.0

    def test_vehicle_two_thirds(self):
        assert abs(get_vat_deduction_rate("vehicle") - 0.6667) < 0.001

    def test_inventory_full(self):
        assert get_vat_deduction_rate("inventory") == 1.0

    def test_unknown_category_returns_zero(self):
        assert get_vat_deduction_rate("unknown_category_xyz") == 0.0


# ── Annual report rules ────────────────────────────────────────────────────────

class TestAnnualReports:
    def test_individual_2025_extended_deadline(self):
        rule = get_annual_report_rule("osek_murshe", 2025)
        assert rule is not None
        assert rule["due_date"] == "2026-06-30"

    def test_company_2025_extended_deadline(self):
        rule = get_annual_report_rule("company_ltd", 2025)
        assert rule is not None
        assert rule["due_date"] == "2026-07-30"

    def test_unknown_entity_returns_none(self):
        result = get_annual_report_rule("employee", 2025)
        assert result is None
