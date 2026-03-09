from datetime import date
from decimal import Decimal

import pytest

from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.clients.models import Client, ClientType
from app.core.exceptions import NotFoundError


def _client(db) -> Client:
    client = Client(
        full_name="AP Create Client",
        id_number="APC-001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_create_payment_success_sets_defaults(test_db):
    client = _client(test_db)
    service = AdvancePaymentService(test_db)

    payment = service.create_payment(
        client_id=client.id,
        year=2026,
        month=2,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("250.50"),
        paid_amount=Decimal("100.00"),
        notes="first advance",
    )

    assert payment.id is not None
    assert payment.client_id == client.id
    assert payment.status.value == "pending"
    assert payment.expected_amount == Decimal("250.50")
    assert payment.paid_amount == Decimal("100.00")
    assert payment.due_date == date(2026, 3, 15)
    assert payment.notes == "first advance"


def test_create_payment_missing_client_raises(test_db):
    service = AdvancePaymentService(test_db)
    with pytest.raises(NotFoundError):
        service.create_payment(
            client_id=999,
            year=2026,
            month=1,
            due_date=date(2026, 2, 15),
        )
