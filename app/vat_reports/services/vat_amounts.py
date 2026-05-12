"""VAT amount derivation from tax rules."""

from decimal import Decimal, ROUND_HALF_UP

from app.vat_reports.integrations.tax_rules_financials import get_vat_rate_percent
from app.vat_reports.models.vat_enums import VatRateType


def calculate_vat_amount(
    net_amount: float | Decimal,
    rate_type: VatRateType | str | None,
    year: int,
) -> Decimal:
    """Derive VAT amount from the annual configured VAT rate."""
    parsed_rate_type = VatRateType(rate_type or VatRateType.STANDARD)
    if parsed_rate_type in (VatRateType.EXEMPT, VatRateType.ZERO_RATE):
        return Decimal("0.00")

    rate_percent = Decimal(str(get_vat_rate_percent(year)))
    amount = Decimal(str(net_amount)) * rate_percent / Decimal("100")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
