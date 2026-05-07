from __future__ import annotations

from datetime import timedelta

from .config import SeedConfig


def tax_calendar_year_range_for_seed(cfg: SeedConfig) -> tuple[int, int]:
    """Return the TaxCalendarEntry year range needed before seed data creation."""
    reference_year = cfg.reference_date.year
    annual_start = reference_year - cfg.annual_reports_per_client

    vat_window_days = max(0, cfg.max_vat_work_items_per_client * 2 * 30)
    earliest_vat_date = cfg.reference_date - timedelta(days=vat_window_days)

    start_year = min(annual_start, earliest_vat_date.year)
    end_year = reference_year + 1
    return start_year, end_year
