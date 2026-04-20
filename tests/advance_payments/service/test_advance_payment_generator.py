from datetime import date
from itertools import count

import pytest

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_generator import generate_annual_schedule
from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType
from app.core.exceptions import NotFoundError


_seq = count(1)


def _business(db) -> Business:
    idx = next(_seq)
    legal_entity = LegalEntity(id_number_type=IdNumberType.INDIVIDUAL, id_number=f"555666{idx:03d}")
    db.add(legal_entity)
    db.commit()
    db.refresh(legal_entity)

    client = Client(
        full_name=f"Advance Gen Client {idx}",
        id_number=legal_entity.id_number,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    business = Business(
        client_id=client.id,
        legal_entity_id=legal_entity.id,
        business_name=f"Advance Gen Business {idx}",
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    business.client_record_id = client.id
    return business


def test_generate_annual_schedule_creates_all_12_months(test_db):
    business = _business(test_db)

    created, skipped = generate_annual_schedule(business.client_record_id, 2026, test_db)

    assert skipped == 0
    assert len(created) == 12
    assert {p.period for p in created} == {f"2026-{m:02d}" for m in range(1, 13)}
    assert all(p.due_date.day == 15 for p in created)


def test_generate_annual_schedule_is_idempotent_for_existing_periods(test_db):
    business = _business(test_db)
    repo = AdvancePaymentRepository(test_db)

    existing = repo.create(
        client_record_id=business.client_record_id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=100,
    )

    created, skipped = generate_annual_schedule(business.client_record_id, 2026, test_db)

    assert skipped == 1
    assert len(created) == 11
    assert all(p.period != existing.period for p in created)

    rows = (
        test_db.query(AdvancePayment)
        .filter(AdvancePayment.client_record_id == business.client_record_id, AdvancePayment.period.like("2026-%"))
        .all()
    )
    assert len(rows) == 12


def test_generate_annual_schedule_missing_business_raises_not_found(test_db):
    with pytest.raises(NotFoundError) as exc:
        generate_annual_schedule(999999, 2026, test_db)

    assert exc.value.code == "ADVANCE_PAYMENT.CLIENT_RECORD_NOT_FOUND"


def test_generate_annual_schedule_bimonthly_due_dates_rollover_year(test_db):
    business = _business(test_db)

    created, skipped = generate_annual_schedule(business.client_record_id, 2026, test_db, period_months_count=2)

    assert skipped == 0
    assert len(created) == 6
    periods = [p.period for p in created]
    assert periods == ["2026-01", "2026-03", "2026-05", "2026-07", "2026-09", "2026-11"]
    nov = next(p for p in created if p.period == "2026-11")
    assert nov.due_date == date(2027, 1, 15)
