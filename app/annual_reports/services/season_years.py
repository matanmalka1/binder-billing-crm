from datetime import date


def get_active_annual_report_tax_year(today: date | None = None) -> int:
    filing_date = today or date.today()
    return filing_date.year - 1


def get_filing_season_year(tax_year: int) -> int:
    return tax_year + 1
