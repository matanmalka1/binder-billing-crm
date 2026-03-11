"""Pure Israeli income tax calculation engine — 2024 brackets."""

from dataclasses import dataclass

_BRACKETS = [
    (81_480, 0.10),
    (116_760, 0.14),
    (187_440, 0.20),
    (260_520, 0.31),
    (557_640, 0.35),
    (None, 0.47),
]

_CREDIT_POINT_VALUE = 2_904.0
_DONATION_CREDIT_RATE = 0.35


@dataclass
class BracketBreakdownItem:
    rate: float
    from_amount: float
    to_amount: float | None
    taxable_in_bracket: float
    tax_in_bracket: float


@dataclass
class TaxCalculationResult:
    taxable_income: float
    pension_deduction: float
    tax_before_credits: float
    credit_points_value: float
    donation_credit: float
    other_credits: float
    tax_after_credits: float
    effective_rate: float
    brackets: list[BracketBreakdownItem]


def calculate_tax(
    taxable_income: float,
    credit_points: float = 2.25,
    pension_deduction: float = 0.0,
    donation_amount: float = 0.0,
    other_credits: float = 0.0,
) -> TaxCalculationResult:
    """Calculate Israeli income tax for 2024 brackets."""
    deduction = min(max(pension_deduction, 0.0), max(taxable_income, 0.0))
    adjusted_income = taxable_income - deduction

    credit_points_value = round(credit_points * _CREDIT_POINT_VALUE, 2)
    donation_credit = round(max(donation_amount, 0.0) * _DONATION_CREDIT_RATE, 2)
    other_credits_val = round(max(other_credits, 0.0), 2)

    if adjusted_income <= 0:
        return TaxCalculationResult(
            taxable_income=round(taxable_income, 2),
            pension_deduction=round(deduction, 2),
            tax_before_credits=0.0,
            credit_points_value=credit_points_value,
            donation_credit=donation_credit,
            other_credits=other_credits_val,
            tax_after_credits=0.0,
            effective_rate=0.0,
            brackets=[],
        )

    tax = 0.0
    prev = 0.0
    brackets: list[BracketBreakdownItem] = []
    for upper, rate in _BRACKETS:
        if upper is None:
            taxable_in_bracket = adjusted_income - prev
            tax_in_bracket = taxable_in_bracket * rate
            tax += tax_in_bracket
            if taxable_in_bracket > 0:
                brackets.append(BracketBreakdownItem(rate, prev, None, round(taxable_in_bracket, 2), round(tax_in_bracket, 2)))
            break
        if adjusted_income <= upper:
            taxable_in_bracket = adjusted_income - prev
            tax_in_bracket = taxable_in_bracket * rate
            tax += tax_in_bracket
            if taxable_in_bracket > 0:
                brackets.append(BracketBreakdownItem(rate, prev, upper, round(taxable_in_bracket, 2), round(tax_in_bracket, 2)))
            break
        taxable_in_bracket = upper - prev
        tax_in_bracket = taxable_in_bracket * rate
        tax += tax_in_bracket
        if taxable_in_bracket > 0:
            brackets.append(BracketBreakdownItem(rate, prev, upper, round(taxable_in_bracket, 2), round(tax_in_bracket, 2)))
        prev = upper

    total_credits = credit_points_value + donation_credit + other_credits_val
    tax_after_credits = max(0.0, tax - total_credits)
    effective_rate = tax_after_credits / taxable_income if taxable_income else 0.0

    return TaxCalculationResult(
        taxable_income=round(taxable_income, 2),
        pension_deduction=round(deduction, 2),
        tax_before_credits=round(tax, 2),
        credit_points_value=credit_points_value,
        donation_credit=donation_credit,
        other_credits=other_credits_val,
        tax_after_credits=round(tax_after_credits, 2),
        effective_rate=round(effective_rate, 6),
        brackets=brackets,
    )


__all__ = ["calculate_tax", "TaxCalculationResult", "BracketBreakdownItem"]
