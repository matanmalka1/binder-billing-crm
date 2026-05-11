from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.enums import ObligationType
from app.tax_calendar.models.deadline_rule import DeadlineRule
from app.tax_calendar.models.tax_calendar_entry import TaxCalendarEntry
from app.tax_calendar.repositories.settings_repository import TaxCalendarSettingsRepository
from app.tax_calendar.services.tax_calendar_entry_service import missing_registry_years

# (obligation_type, period_months_count) → expected count per year
# None for period_months_count = annual (no period)
_EXPECTED_BREAKDOWN: dict[tuple[ObligationType, int | None], int] = {
    (ObligationType.VAT, 1): 12,
    (ObligationType.VAT, 2): 6,
    (ObligationType.ADVANCE_PAYMENT, 1): 12,
    (ObligationType.ADVANCE_PAYMENT, 2): 6,
    (ObligationType.ANNUAL_REPORT, None): 1,
}


def list_rules(db: Session) -> list[DeadlineRule]:
    return TaxCalendarSettingsRepository(db).list_rules()


def list_entries(
    db: Session,
    *,
    start_year: int | None,
    end_year: int | None,
) -> list[TaxCalendarEntry]:
    return TaxCalendarSettingsRepository(db).list_entries(
        start_year=start_year, end_year=end_year
    )


def get_summary(
    db: Session,
    *,
    start_year: int | None,
    end_year: int | None,
) -> dict:
    repo = TaxCalendarSettingsRepository(db)
    rows = repo.count_by_year_obligation_months(start_year=start_year, end_year=end_year)

    # Build per-year breakdown keyed by "{obligation_type}_{months_count or 'annual'}"
    per_year: dict[int, dict[str, int]] = {}
    actual: dict[tuple[int, ObligationType, int | None], int] = {}
    for tax_year, obligation_type_val, period_months_count, count in rows:
        obligation = ObligationType(obligation_type_val)
        label = _summary_label(obligation, period_months_count)
        per_year.setdefault(tax_year, {})[label] = count
        actual[(tax_year, obligation, period_months_count)] = count

    warnings: list[str] = []
    # Check all years in range, not just those with entries
    if start_year is not None and end_year is not None:
        years_to_check = range(start_year, end_year + 1)
    else:
        years_to_check = sorted(per_year.keys())
    for year in years_to_check:
        for (obtype, months), expected_count in _EXPECTED_BREAKDOWN.items():
            found = actual.get((year, obtype, months), 0)
            if found != expected_count:
                label = _summary_label(obtype, months)
                warnings.append(
                    f"Year {year}: {label} — expected {expected_count}, found {found}."
                )

    # Warn for years using DeadlineRule fallback (no official registry calendar)
    if start_year is not None and end_year is not None:
        for year in missing_registry_years(start_year, end_year):
            warnings.append(
                f"Year {year} uses fallback DeadlineRule dates because official "
                f"tax calendar registry data is missing."
            )
    elif per_year:
        all_years = sorted(per_year.keys())
        for year in missing_registry_years(all_years[0], all_years[-1]):
            if year in per_year:
                warnings.append(
                    f"Year {year} uses fallback DeadlineRule dates because official "
                    f"tax calendar registry data is missing."
                )

    total_entries = sum(c for year_data in per_year.values() for c in year_data.values())

    return {
        "start_year": start_year,
        "end_year": end_year,
        "total_entries": total_entries,
        "per_year": per_year,
        "warnings": warnings,
    }


def _summary_label(obligation: ObligationType, months: int | None) -> str:
    if months is None:
        return f"{obligation.value}_annual"
    return f"{obligation.value}_{months}m"
