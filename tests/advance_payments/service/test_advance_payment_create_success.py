from datetime import date
from decimal import Decimal
from itertools import count

import pytest

from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.businesses.models.business import Business, BusinessType
from app.businesses.models.business import BusinessStatus
from app.clients.models.client import Client
from app.core.exceptions import NotFoundError, ForbiddenError


_seq = count(1)


def _business(db, *, status: BusinessStatus = BusinessStatus.ACTIVE) -> Business:
    idx = next(_seq)
    client = Client(full_name=f"AP Create Client {idx}", id_number=f"991199{idx:03d}")
    db.add(client)
    db.commit()
    db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"AP Create Business {idx}",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
        status=status,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def test_create_payment_success_sets_defaults(test_db):
    business = _business(test_db)
    service = AdvancePaymentService(test_db)

    payment = service.create_payment(
        business_id=business.id,
        period="2026-02",
        period_months_count=1,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("250.50"),
        paid_amount=Decimal("100.00"),
        notes="first advance",
    )

    assert payment.id is not None
    assert payment.business_id == business.id
    assert payment.status.value == "pending"
    assert payment.expected_amount == Decimal("250.50")
    assert payment.paid_amount == Decimal("100.00")
    assert payment.due_date == date(2026, 3, 15)
    assert payment.notes == "first advance"


def test_create_payment_missing_business_raises(test_db):
    service = AdvancePaymentService(test_db)
    with pytest.raises(NotFoundError):
        service.create_payment(
            business_id=999,
            period="2026-01",
            period_months_count=1,
            due_date=date(2026, 2, 15),
        )


def test_create_payment_closed_business_raises_business_closed(test_db):
    business = _business(test_db, status=BusinessStatus.CLOSED)
    service = AdvancePaymentService(test_db)

    with pytest.raises(ForbiddenError) as exc_info:
        service.create_payment(
            business_id=business.id,
            period="2026-05",
            period_months_count=1,
            due_date=date(2026, 6, 15),
        )

    assert getattr(exc_info.value, "code", None) == "BUSINESS.CLOSED"
