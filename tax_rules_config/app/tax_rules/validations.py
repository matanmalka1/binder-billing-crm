from __future__ import annotations

from .types import ClientTaxProfile, EntityType, ReportingFrequency

# ── Validation functions ───────────────────────────────────────────────────────
# כל פונקציה מחזירה str (שגיאה בעברית) או None (תקין).
# קוד קורא: אסוף את כל השגיאות ועבד לפי הצורך.


def validate_osek_patur_no_periodic_vat(profile: ClientTaxProfile) -> str | None:
    """עוסק פטור לא יכול לקבל דוח מע״מ תקופתי."""
    if profile.get("entity_type") == EntityType.OSEK_PATUR:
        freq = profile.get("vat_reporting_frequency")
        if freq in (ReportingFrequency.MONTHLY, ReportingFrequency.BIMONTHLY):
            return (
                "עוסק פטור אינו מגיש דוחות מע״מ תקופתיים. "
                "תדירות מע״מ חייבת להיות 'exempt' או ריקה."
            )
    return None


def validate_company_no_self_employed_ni(profile: ClientTaxProfile) -> str | None:
    """חברה בע"מ לא משלמת ביטוח לאומי כעצמאי."""
    if profile.get("entity_type") == EntityType.COMPANY_LTD:
        if profile.get("btl_status") == "self_employed":
            return (
                "חברה בע״מ אינה מסווגת כעצמאי בביטוח לאומי. "
                "בדוק חובת מעסיק (טופס 102) בנפרד."
            )
    return None


def validate_no_duplicate_annual_report(
    existing_tax_years: list[int], new_tax_year: int
) -> str | None:
    """אין דוח שנתי כפול לאותה שנת מס."""
    if new_tax_year in existing_tax_years:
        return f"דוח שנתי לשנת המס {new_tax_year} כבר קיים."
    return None


def validate_advance_requires_rate(profile: ClientTaxProfile) -> str | None:
    """אין מקדמות מס הכנסה בלי אחוז מקדמה."""
    freq = profile.get("income_tax_advance_frequency")
    if freq in (ReportingFrequency.MONTHLY, ReportingFrequency.BIMONTHLY):
        rate = profile.get("income_tax_advance_rate")
        if rate is None:
            return (
                "לקוח עם מקדמות מס הכנסה חייב שדה income_tax_advance_rate מוגדר."
            )
    return None


def validate_pcn874_requires_flag(profile: ClientTaxProfile) -> str | None:
    """אין PCN874 בלי סימון מתאים."""
    # אם מישהו מנסה לייצר PCN874 ל-client ללא הדגל
    if profile.get("_generate_pcn874") and not profile.get("requires_pcn874"):
        return (
            "לא ניתן לייצר דוח PCN874 ללא שדה requires_pcn874=True על הלקוח."
        )
    return None


def validate_employee_no_vat(profile: ClientTaxProfile) -> str | None:
    """שכיר לא מקבל שום דוח מע״מ."""
    if profile.get("entity_type") == EntityType.EMPLOYEE:
        freq = profile.get("vat_reporting_frequency")
        if freq and freq != ReportingFrequency.NONE:
            return "שכיר אינו חייב בדיווחי מע״מ מכל סוג."
    return None


def validate_withholding_126_requires_employees(profile: ClientTaxProfile) -> str | None:
    """טופס 126 רלוונטי רק למי שיש עובדים."""
    if profile.get("_generate_form_126") and not profile.get("has_employees"):
        return "טופס 126 מתאים למעסיקים בלבד — has_employees חייב להיות True."
    return None


def validate_btl_self_employed_requires_advance_amount(profile: ClientTaxProfile) -> str | None:
    """עצמאי בביטוח לאומי ללא סכום מקדמה."""
    if profile.get("btl_status") == "self_employed":
        if profile.get("btl_advance_amount") is None:
            return (
                "עצמאי בביטוח לאומי חייב שדה btl_advance_amount מוגדר "
                "לצורך חישוב המקדמה החודשית."
            )
    return None


def validate_company_vat_has_frequency(profile: ClientTaxProfile) -> str | None:
    """חברה בע"מ ועוסק מורשה חייבים תדירות מע״מ מוגדרת."""
    entity = profile.get("entity_type")
    if entity in (EntityType.COMPANY_LTD, EntityType.OSEK_MURSHE):
        freq = profile.get("vat_reporting_frequency")
        if not freq or freq == ReportingFrequency.NONE:
            return (
                f"{entity} חייב שדה vat_reporting_frequency מוגדר "
                f"(monthly / bimonthly)."
            )
    return None


# ── runner — מריץ את כל הvalidations ────────────────────────────────────────

_ALL_VALIDATORS = [
    validate_osek_patur_no_periodic_vat,
    validate_company_no_self_employed_ni,
    validate_advance_requires_rate,
    validate_pcn874_requires_flag,
    validate_employee_no_vat,
    validate_withholding_126_requires_employees,
    validate_btl_self_employed_requires_advance_amount,
    validate_company_vat_has_frequency,
]


def validate_profile(profile: ClientTaxProfile) -> list[str]:
    """מריץ את כל הvalidations על פרופיל לקוח. מחזיר רשימת שגיאות (ריקה = תקין)."""
    errors = []
    for validator in _ALL_VALIDATORS:
        result = validator(profile)
        if result:
            errors.append(result)
    return errors
