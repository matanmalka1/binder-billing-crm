from datetime import date
from decimal import Decimal
from itertools import count

import pytest

from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.clients.models.client import Client, ClientStatus
from app.core.exceptions import NotFoundError, ForbiddenError


_seq = count(1)


def _client(db, *, status: ClientStatus = ClientStatus.ACTIVE) -> Client:
    idx = next(_seq)
    client = Client(
        full_name=f"AP Create Client {idx}",
        id_number=f"991199{idx:03d}",
        status=status,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_create_payment_success_sets_defaults(test_db):
    client = _client(test_db)
    service = AdvancePaymentService(test_db)

    payment = service.create_payment_for_client(
        client_id=client.id,
        period="2026-02",
        period_months_count=1,
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


def test_create_payment_missing_business_raises(test_db):
    service = AdvancePaymentService(test_db)
    with pytest.raises(NotFoundError):
        service.create_payment_for_client(
            client_id=999,
            period="2026-01",
            period_months_count=1,
            due_date=date(2026, 2, 15),
        )


def test_create_payment_closed_client_raises_client_closed(test_db):
    client = _client(test_db, status=ClientStatus.CLOSED)
    service = AdvancePaymentService(test_db)

    with pytest.raises(ForbiddenError) as exc_info:
        service.create_payment_for_client(
            client_id=client.id,
            period="2026-05",
            period_months_count=1,
            due_date=date(2026, 6, 15),
        )

    assert getattr(exc_info.value, "code", None) == "CLIENT.CLOSED"
