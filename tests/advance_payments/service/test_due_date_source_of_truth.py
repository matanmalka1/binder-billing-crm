"""Regression tests: advance payment due_date comes from TaxCalendarEntry, not build_due_date()."""

from datetime import date

from app.advance_payments.services.advance_payment_generator import (
    generate_annual_schedule,
)
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.common.enums import DeadlineRuleType, ObligationType
from tests.tax_calendar.service.linking_helpers import advance_client, make_entry


def test_advance_payment_due_date_from_entry_not_hardcoded_15(test_db):
    """Regression: when TaxCalendarEntry.due_date=2026-02-16, payment must store 2026-02-16, not 2026-02-15."""
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.ADVANCE_PAYMENT,
        rule_type=DeadlineRuleType.ADVANCE_MONTHLY,
        period="2026-01",
        months=1,
        tax_year=2026,
    )
    # Simulate a holiday shift: tax authority moves deadline from 15th to 16th.
    entry.due_date = date(2026, 2, 16)
    test_db.flush()

    client = advance_client(test_db)
    created, skipped = generate_annual_schedule(
        client.id, 2026, test_db, reference_date=date(2025, 12, 31)
    )

    jan = next(p for p in created if p.period == "2026-01")

    assert jan.due_date == date(2026, 2, 16), (
        f"expected 2026-02-16 from TaxCalendarEntry, got {jan.due_date} (hardcoded 15th is wrong)"
    )
    assert jan.due_date_original == date(2026, 2, 16)
    assert jan.due_date_effective == date(2026, 2, 16)
    assert jan.tax_calendar_entry_id == entry.id


def test_generate_advance_payment_all_periods_use_entry_due_date(test_db):
    """When entry exists with custom date, all generated payments for that period use entry.due_date."""
    entry_feb = make_entry(
        test_db,
        obligation_type=ObligationType.ADVANCE_PAYMENT,
        rule_type=DeadlineRuleType.ADVANCE_MONTHLY,
        period="2026-02",
        months=1,
        tax_year=2026,
    )
    entry_feb.due_date = date(2026, 3, 17)
    test_db.flush()

    client = advance_client(test_db)
    created, _ = generate_annual_schedule(
        client.id, 2026, test_db, reference_date=date(2025, 12, 31)
    )

    feb = next(p for p in created if p.period == "2026-02")
    assert feb.due_date == date(2026, 3, 17)
    assert feb.due_date_original == date(2026, 3, 17)
    assert feb.due_date_effective == date(2026, 3, 17)


def test_create_payment_directly_uses_entry_due_date(test_db):
    """create_payment_for_client ignores caller-supplied due_date, uses TaxCalendarEntry.due_date."""
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.ADVANCE_PAYMENT,
        rule_type=DeadlineRuleType.ADVANCE_MONTHLY,
        period="2026-03",
        months=1,
        tax_year=2026,
    )
    entry.due_date = date(2026, 4, 16)
    test_db.flush()

    client = advance_client(test_db)
    service = AdvancePaymentService(test_db)
    payment = service.create_payment_for_client(
        client_record_id=client.id,
        period="2026-03",
        period_months_count=1,
        due_date=date(
            2026, 4, 15
        ),  # caller passes 15th; must be ignored in favor of entry's 16th
    )

    assert payment.due_date == date(2026, 4, 16)
    assert payment.due_date_original == date(2026, 4, 16)
    assert payment.due_date_effective == date(2026, 4, 16)


def test_link_advance_payment_backfills_missing_snapshots(test_db):
    """link_advance_payment sets due_date_original/effective from entry when they are None."""
    from app.tax_calendar.services.materialization_service import (
        TaxCalendarMaterializationService,
    )
    from app.advance_payments.models.advance_payment import AdvancePayment

    entry = make_entry(
        test_db,
        obligation_type=ObligationType.ADVANCE_PAYMENT,
        rule_type=DeadlineRuleType.ADVANCE_MONTHLY,
        period="2026-05",
        months=1,
        tax_year=2026,
    )
    entry.due_date = date(2026, 6, 16)
    test_db.flush()

    # Build a payment that has no snapshot fields yet (simulating a direct insert bypassing service)
    payment = AdvancePayment(
        client_record_id=1,
        period="2026-05",
        period_months_count=1,
        due_date=date(2026, 6, 15),
        tax_calendar_entry_id=entry.id,
    )
    # Manually bypass snapshot events by setting originals to None (mimicking legacy row)
    payment.due_date_original = None
    payment.due_date_effective = None

    mat = TaxCalendarMaterializationService(test_db)
    mat.link_advance_payment(payment)

    assert payment.due_date_original == date(2026, 6, 16)
    assert payment.due_date_effective == date(2026, 6, 16)
