"""Pure Israeli income tax calculation engine — 2024 brackets."""

from dataclasses import dataclass

# 2024 tax brackets: (upper_bound, rate)  — last bracket has no upper bound
_BRACKETS = [
    (81_480,   0.10),
    (116_760,  0.14),
    (187_440,  0.20),
    (260_520,  0.31),
    (557_640,  0.35),
    (None,     0.47),
]

_CREDIT_POINT_VALUE = 2_904.0  # ₪ per credit point, 2024


@dataclass
class TaxCalculationResult:
    taxable_income: float
    tax_before_credits: float
    credit_points_value: float
    tax_after_credits: float
    effective_rate: float


def calculate_tax(
    taxable_income: float,
    credit_points: float = 2.25,
) -> TaxCalculationResult:
    """Calculate Israeli income tax for 2024 brackets."""
    if taxable_income <= 0:
        return TaxCalculationResult(
            taxable_income=taxable_income,
            tax_before_credits=0.0,
            credit_points_value=round(credit_points * _CREDIT_POINT_VALUE, 2),
            tax_after_credits=0.0,
            effective_rate=0.0,
        )

    tax = 0.0
    prev = 0.0
    for upper, rate in _BRACKETS:
        if upper is None:
            tax += (taxable_income - prev) * rate
            break
        if taxable_income <= upper:
            tax += (taxable_income - prev) * rate
            break
        tax += (upper - prev) * rate
        prev = upper

    credit_points_value = round(credit_points * _CREDIT_POINT_VALUE, 2)
    tax_after_credits = max(0.0, tax - credit_points_value)
    effective_rate = tax_after_credits / taxable_income if taxable_income else 0.0

    return TaxCalculationResult(
        taxable_income=round(taxable_income, 2),
        tax_before_credits=round(tax, 2),
        credit_points_value=credit_points_value,
        tax_after_credits=round(tax_after_credits, 2),
        effective_rate=round(effective_rate, 6),
    )


__all__ = ["calculate_tax", "TaxCalculationResult"]
