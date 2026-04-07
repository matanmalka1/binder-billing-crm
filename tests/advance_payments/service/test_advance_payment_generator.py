from datetime import date
from itertools import count

import pytest

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_generator import generate_annual_schedule
from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client
from app.core.exceptions import NotFoundError


_seq = count(1)


def _business(db) -> Business:
    idx = next(_seq)
    client = Client(
        full_name=f"Advance Gen Client {idx}",
        id_number=f"555666{idx:03d}",
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Advance Gen Business {idx}",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def test_generate_annual_schedule_creates_all_12_months(test_db):
    business = _business(test_db)

    created, skipped = generate_annual_schedule(business.id, 2026, test_db)

    assert skipped == 0
    assert len(created) == 12
    assert {p.period for p in created} == {f"2026-{m:02d}" for m in range(1, 13)}
    assert all(p.due_date.day == 15 for p in created)


def test_generate_annual_schedule_is_idempotent_for_existing_periods(test_db):
    business = _business(test_db)
    repo = AdvancePaymentRepository(test_db)

    existing = repo.create(
        business_id=business.id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=100,
    )

    created, skipped = generate_annual_schedule(business.id, 2026, test_db)

    assert skipped == 1
    assert len(created) == 11
    assert all(p.period != existing.period for p in created)

    rows = (
        test_db.query(AdvancePayment)
        .filter(AdvancePayment.business_id == business.id, AdvancePayment.period.like("2026-%"))
        .all()
    )
    assert len(rows) == 12


def test_generate_annual_schedule_missing_business_raises_not_found(test_db):
    with pytest.raises(NotFoundError) as exc:
        generate_annual_schedule(999999, 2026, test_db)

    assert exc.value.code == "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND"


def test_generate_annual_schedule_bimonthly_due_dates_rollover_year(test_db):
    business = _business(test_db)

    created, skipped = generate_annual_schedule(business.id, 2026, test_db, period_months_count=2)

    assert skipped == 0
    assert len(created) == 6
    periods = [p.period for p in created]
    assert periods == ["2026-01", "2026-03", "2026-05", "2026-07", "2026-09", "2026-11"]
    nov = next(p for p in created if p.period == "2026-11")
    assert nov.due_date == date(2026, 11, 15)
