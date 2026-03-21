"""
Pure calculation functions for advance payment suggestions.
No DB access — all inputs are passed as arguments.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.core.exceptions import AppError


def derive_annual_income_from_vat(
    total_output_vat: Decimal,
    vat_rate: Decimal = Decimal("0.18"),
) -> Decimal:
    """Reverse-calculate annual taxable income from total output VAT."""
    if vat_rate == 0:
        raise AppError("שיעור המע״מ לא יכול להיות אפס", "ADVANCE_PAYMENT.RATE_INVALID")
    return total_output_vat / vat_rate


def calculate_expected_amount(
    annual_income: Decimal,
    advance_rate: Decimal,
) -> Decimal:
    """
    Monthly advance payment = (annual_income * advance_rate / 100) / 12,
    rounded to the nearest whole shekel.
    """
    monthly = (annual_income * advance_rate / Decimal("100")) / Decimal("12")
    return monthly.quantize(Decimal("1"), rounding=ROUND_HALF_UP)