"""Adapter for tax_rules registry access used by annual reports."""

from decimal import Decimal


def get_default_resident_credit_points(tax_year: int) -> Decimal:
    try:
        from tax_rules.registry import get_credit_point_config

        return Decimal(str(get_credit_point_config(tax_year).default_resident_points))
    except Exception:
        return Decimal("2.25")


def get_credit_point_annual_value(tax_year: int) -> float:
    from tax_rules.registry import get_credit_point_config

    return float(get_credit_point_config(tax_year).annual_value_ils)


def get_income_tax_brackets_for_year(tax_year: int):
    from tax_rules import get_income_tax_brackets

    return get_income_tax_brackets(tax_year)


def get_ni_brackets_for_year(tax_year: int):
    from tax_rules import get_ni_brackets

    return get_ni_brackets(tax_year)


def get_supported_tax_years() -> list[int]:
    from tax_rules.registry import get_supported_years

    return list(get_supported_years())
