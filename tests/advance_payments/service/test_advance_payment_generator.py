from datetime import date
from itertools import count

import pytest

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_generator import generate_annual_schedule
from app.clients.models import Client, ClientType
from app.core.exceptions import NotFoundError


_client_seq = count(1)


def _client(db) -> Client:
    idx = next(_client_seq)
    crm_client = Client(
        full_name=f"Advance Gen Client {idx}",
        id_number=f"APG{idx:06d}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def test_generate_annual_schedule_creates_all_12_months(test_db):
    crm_client = _client(test_db)

    created, skipped = generate_annual_schedule(crm_client.id, 2026, test_db)

    assert skipped == 0
    assert len(created) == 12
    assert {p.month for p in created} == set(range(1, 13))
    assert all(p.due_date.day == 15 for p in created)


def test_generate_annual_schedule_is_idempotent_for_existing_months(test_db):
    crm_client = _client(test_db)
    repo = AdvancePaymentRepository(test_db)

    existing = repo.create(
        client_id=crm_client.id,
        year=2026,
        month=1,
        due_date=date(2026, 1, 15),
        expected_amount=100,
    )

    created, skipped = generate_annual_schedule(crm_client.id, 2026, test_db)

    assert skipped == 1
    assert len(created) == 11
    assert all(p.month != existing.month for p in created)

    rows = test_db.query(AdvancePayment).filter(AdvancePayment.client_id == crm_client.id, AdvancePayment.year == 2026).all()
    assert len(rows) == 12


def test_generate_annual_schedule_missing_client_raises_not_found(test_db):
    with pytest.raises(NotFoundError) as exc:
        generate_annual_schedule(999999, 2026, test_db)

    assert exc.value.code == "ADVANCE_PAYMENT.CLIENT_NOT_FOUND"
