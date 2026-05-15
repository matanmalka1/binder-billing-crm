from datetime import date

from app.common.period_utils import (
    bimonthly_advance_payment_period,
    bimonthly_vat_period,
    monthly_vat_period,
)


def test_monthly_period_is_previous_month():
    assert monthly_vat_period(date(2026, 4, 10)) == ("2026-03", "מרץ 2026")


def test_bimonthly_period_is_reportable_pair_not_current_pair():
    assert bimonthly_vat_period(date(2026, 4, 10)) == (
        "2026-01",
        "ינואר-פברואר 2026",
    )


def test_bimonthly_period_uses_pair_that_just_closed():
    assert bimonthly_vat_period(date(2026, 5, 10)) == (
        "2026-03",
        "מרץ-אפריל 2026",
    )


def test_bimonthly_advance_period_uses_first_month_of_pair():
    assert bimonthly_advance_payment_period(date(2026, 5, 10)) == (
        "2026-03",
        "מרץ-אפריל 2026",
    )
