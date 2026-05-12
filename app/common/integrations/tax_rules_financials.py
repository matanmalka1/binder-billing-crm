from decimal import Decimal


def get_vat_rate_percent(year: int) -> Decimal | None:
    try:
        from tax_rules.registry import get_financial

        return Decimal(str(get_financial(year, "vat_rate_percent").value))
    except Exception:
        return None
