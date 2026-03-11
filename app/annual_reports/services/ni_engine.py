"""National Insurance (ביטוח לאומי) calculation engine — 2024."""

from dataclasses import dataclass

_NI_MONTHLY_CEILING = 7_522.0
_NI_ANNUAL_CEILING = _NI_MONTHLY_CEILING * 12
_NI_RATE_BASE = 0.0597
_NI_RATE_HIGH = 0.1783


@dataclass
class NationalInsuranceResult:
    base_amount: float
    high_amount: float
    total: float


def calculate_national_insurance(income: float) -> NationalInsuranceResult:
    """Calculate Israeli National Insurance for annual income in 2024 rates."""
    income = max(income, 0.0)
    base = min(income, _NI_ANNUAL_CEILING)
    above = max(income - _NI_ANNUAL_CEILING, 0.0)
    base_amount = round(base * _NI_RATE_BASE, 2)
    high_amount = round(above * _NI_RATE_HIGH, 2)
    return NationalInsuranceResult(
        base_amount=base_amount,
        high_amount=high_amount,
        total=round(base_amount + high_amount, 2),
    )


__all__ = ["calculate_national_insurance", "NationalInsuranceResult"]
