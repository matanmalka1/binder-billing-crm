from datetime import date
from decimal import Decimal
from itertools import count

import pytest

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_calculator import (
    calculate_expected_amount,
    derive_annual_income_from_vat,
)
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.clients.models import Client, ClientType
from app.clients.models.client_tax_profile import ClientTaxProfile
from app.core.exceptions import AppError, ConflictError
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.models.vat_enums import VatWorkItemStatus


_client_seq = count(1)


def _client(db) -> Client:
    client = Client(
        full_name="Advance Service Client",
        id_number=f"77777777{next(_client_seq)}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_create_payment_duplicate_month_raises_conflict(test_db):
    client = _client(test_db)
    service = AdvancePaymentService(test_db)

    service.create_payment(client_id=client.id, year=2026, month=1, due_date=date(2026, 2, 15))

    with pytest.raises(ConflictError):
        service.create_payment(client_id=client.id, year=2026, month=1, due_date=date(2026, 2, 15))


def test_suggest_expected_amount_requires_profile_and_vat(test_db, test_user):
    client = _client(test_db)
    service = AdvancePaymentService(test_db)

    assert service.suggest_expected_amount(client.id, 2026) is None

    profile = ClientTaxProfile(client_id=client.id, advance_rate=Decimal("6.0"))
    test_db.add(profile)
    test_db.commit()

    with pytest.raises(AttributeError):
        service.suggest_expected_amount(client.id, 2026)

    vat_item = VatWorkItem(
        client_id=client.id,
        created_by=test_user.id,
        period="2025-02",
        status=VatWorkItemStatus.FILED,
        total_output_vat=Decimal("18000"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("18000"),
    )
    test_db.add(vat_item)
    test_db.commit()

    with pytest.raises(AttributeError):
        service.suggest_expected_amount(client.id, 2026)


def test_calculate_expected_amount_rounds_half_up():
    amount = calculate_expected_amount(Decimal("1000"), Decimal("10"))
    assert amount == Decimal("8")


def test_derive_income_zero_rate_raises():
    with pytest.raises(AppError) as exc_info:
        derive_annual_income_from_vat(Decimal("1000"), vat_rate=Decimal("0"))
    assert exc_info.value.code == "ADVANCE_PAYMENT.RATE_INVALID"
