from __future__ import annotations

from .obligations.income_tax import ANNUAL_REPORT_RULES, ANNUAL_REPORT_ATTACHMENTS, INCOME_TAX_ADVANCE_RULES
from .obligations.national_insurance import NATIONAL_INSURANCE_RULES
from .obligations.vat import VAT_RULES
from .obligations.withholding import WITHHOLDING_RULES
from .obligations.annual_reports import ANNUAL_REPORT_RULES_V2
from .types import (
    AnnualReportRule,
    BtlStatus,
    ClientTaxProfile,
    EntityType,
    ObligationRule,
    ObligationScope,
    ReportingFrequency,
)

ALL_OBLIGATION_RULES: tuple[ObligationRule, ...] = (
    *VAT_RULES,
    *INCOME_TAX_ADVANCE_RULES,
    *NATIONAL_INSURANCE_RULES,
    *WITHHOLDING_RULES,
)


def _scope_matches(scope: ObligationScope, profile: ClientTaxProfile) -> bool:
    """בדוק האם פרופיל לקוח עומד בתנאי התחולה של חוק."""

    # entity_type
    if scope.entity_types:
        entity = profile.get("entity_type")
        if EntityType(str(entity)) not in scope.entity_types:
            return False

    # vat_frequencies
    if scope.vat_frequencies:
        freq = profile.get("vat_reporting_frequency")
        try:
            parsed = ReportingFrequency(str(freq)) if freq else None
        except ValueError:
            parsed = None
        if parsed not in scope.vat_frequencies:
            return False

    # advance_frequencies
    if scope.advance_frequencies:
        freq = profile.get("income_tax_advance_frequency")
        try:
            parsed = ReportingFrequency(str(freq)) if freq else None
        except ValueError:
            parsed = None
        if parsed not in scope.advance_frequencies:
            return False

    # btl_statuses
    if scope.btl_statuses:
        status = profile.get("btl_status")
        try:
            parsed_btl = BtlStatus(str(status)) if status else None
        except ValueError:
            parsed_btl = None
        if parsed_btl not in scope.btl_statuses:
            return False

    # boolean fields
    if scope.requires_pcn874 is not None:
        if bool(profile.get("requires_pcn874")) != scope.requires_pcn874:
            return False

    if scope.has_employees is not None:
        if bool(profile.get("has_employees")) != scope.has_employees:
            return False

    if scope.has_withholding_file is not None:
        if bool(profile.get("has_withholding_file")) != scope.has_withholding_file:
            return False

    if scope.has_representative is not None:
        if bool(profile.get("has_representative")) != scope.has_representative:
            return False

    return True


def resolve_obligation_rules(profile: ClientTaxProfile) -> list[ObligationRule]:
    """
    מחזיר את חובות הדיווח/תשלום הרלוונטיות לפרופיל לקוח.

    שדות נדרשים:
      entity_type: osek_patur | osek_murshe | company_ltd | employee
      vat_reporting_frequency: monthly | bimonthly | exempt | none
      income_tax_advance_frequency: monthly | bimonthly | none
      btl_status: self_employed | employee | not_self_employed | unknown
      has_employees: bool
      has_withholding_file: bool
      requires_pcn874: bool
      has_representative: bool
    """
    return [
        rule
        for rule in ALL_OBLIGATION_RULES
        if _scope_matches(rule.scope, profile)
    ]


def resolve_annual_report_rule(
    entity_type: str, tax_year: int
) -> dict | None:
    """מחזיר חוק דוח שנתי לפי סוג ישות ושנת מס."""
    try:
        parsed = EntityType(entity_type)
    except ValueError:
        return None

    for rule in ANNUAL_REPORT_RULES_V2:
        if rule.is_attachment:
            continue
        if parsed in rule.scope.entity_types:
            due_date = rule.tax_year_specific_due_dates.get(tax_year)
            return {
                "id": rule.id,
                "form": rule.form,
                "label_he": rule.label_he,
                "tax_year": tax_year,
                "due_date": due_date or f"{rule.default_due_month:02d}/{tax_year + 1}",
                "notes_he": rule.notes_he,
            }
    return None
