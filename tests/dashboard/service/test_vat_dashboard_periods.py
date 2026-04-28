from datetime import date

from app.dashboard.services.vat_dashboard_periods import (
    bimonthly_vat_period,
    monthly_vat_period,
)


def test_monthly_period_is_previous_month():
    assert monthly_vat_period(date(2026, 4, 10)) == ("2026-03", "מרץ 2026")


def test_bimonthly_period_is_reportable_pair_not_current_pair():
    assert bimonthly_vat_period(date(2026, 4, 10)) == (
        "2026-02",
        "ינואר-פברואר 2026",
    )


def test_bimonthly_period_uses_pair_that_just_closed():
    assert bimonthly_vat_period(date(2026, 5, 10)) == (
        "2026-04",
        "מרץ-אפריל 2026",
    )
