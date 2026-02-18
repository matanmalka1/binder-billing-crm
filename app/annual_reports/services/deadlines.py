from datetime import datetime


def standard_deadline(tax_year: int) -> datetime:
    """April 30 of the year following the tax year."""
    return datetime(tax_year + 1, 4, 30, 23, 59, 59)


def extended_deadline(tax_year: int) -> datetime:
    """January 31 two years after the tax year (for authorised reps)."""
    return datetime(tax_year + 2, 1, 31, 23, 59, 59)


__all__ = ["standard_deadline", "extended_deadline"]
