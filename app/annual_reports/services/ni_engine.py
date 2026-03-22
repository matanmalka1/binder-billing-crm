"""National Insurance (ביטוח לאומי) calculation engine — multi-year."""

from dataclasses import dataclass

from app.annual_reports.services.constants import NI_RATE_BASE as _NI_RATE_BASE, NI_RATE_HIGH as _NI_RATE_HIGH

_NI_CEILING_BY_YEAR: dict[int, float] = {
    2024: 90_264.0,
    2025: 93_384.0,
    2026: 93_384.0,  # PLACEHOLDER — update when NII publishes 2026 ceiling
}


@dataclass
class NationalInsuranceResult:
    base_amount: float
    high_amount: float
    total: float


def calculate_national_insurance(income: float, tax_year: int = 2024) -> NationalInsuranceResult:
    """Calculate Israeli National Insurance for the given tax year."""
    ceiling = _NI_CEILING_BY_YEAR.get(tax_year, _NI_CEILING_BY_YEAR[2024])
    income = max(income, 0.0)
    base = min(income, ceiling)
    above = max(income - ceiling, 0.0)
    base_amount = round(base * _NI_RATE_BASE, 2)
    high_amount = round(above * _NI_RATE_HIGH, 2)
    return NationalInsuranceResult(
        base_amount=base_amount,
        high_amount=high_amount,
        total=round(base_amount + high_amount, 2),
    )


__all__ = ["calculate_national_insurance", "NationalInsuranceResult"]
