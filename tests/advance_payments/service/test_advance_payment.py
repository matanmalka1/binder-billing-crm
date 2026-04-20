from datetime import date
from decimal import Decimal
from itertools import count

import pytest

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.services.advance_payment_calculator import (
    calculate_expected_amount,
    derive_annual_income_from_vat,
)
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.businesses.models.business import Business
from app.common.enums import VatType
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType
from app.core.exceptions import AppError, ConflictError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


_seq = count(1)


def _business(db) -> Business:
    idx = next(_seq)
    legal_entity = LegalEntity(id_number_type=IdNumberType.INDIVIDUAL, 
        id_number=f"777777{idx:03d}",
        vat_reporting_frequency=VatType.MONTHLY,
    )
    db.add(legal_entity)
    db.commit()
    db.refresh(legal_entity)

    client = Client(
        full_name=f"Advance Service Client {idx}",
        id_number=legal_entity.id_number,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    business = Business(
        client_id=client.id,
        legal_entity_id=legal_entity.id,
        business_name=f"Advance Service Business {idx}",
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    business.client_record_id = client.id
    business.legal_entity = legal_entity
    return business


def test_create_payment_duplicate_period_raises_conflict(test_db):
    business = _business(test_db)
    service = AdvancePaymentService(test_db)

    service.create_payment_for_client(
        client_record_id=business.client_record_id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
    )

    with pytest.raises(ConflictError):
        service.create_payment_for_client(
            client_record_id=business.client_record_id,
            period="2026-01",
            period_months_count=1,
            due_date=date(2026, 2, 15),
        )


def test_suggest_expected_amount_requires_profile_and_vat(test_db, test_user):
    business = _business(test_db)
    service = AdvancePaymentService(test_db)

    assert service.suggest_expected_amount_for_client(business.client_record_id, 2026) is None

    business.legal_entity.advance_rate = Decimal("6.0")
    test_db.commit()

    assert service.suggest_expected_amount_for_client(business.client_record_id, 2026) is None

    vat_item = VatWorkItem(
        client_record_id=business.client_record_id,
        created_by=test_user.id,
        period="2025-02",
        period_type=VatType.MONTHLY,
        status=VatWorkItemStatus.FILED,
        total_output_vat=Decimal("18000"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("18000"),
    )
    test_db.add(vat_item)
    test_db.commit()

    assert service.suggest_expected_amount_for_client(business.client_record_id, 2026) == Decimal("500")


def test_calculate_expected_amount_rounds_half_up():
    amount = calculate_expected_amount(Decimal("1000"), Decimal("10"))
    assert amount == Decimal("8")


def test_derive_income_zero_rate_raises():
    with pytest.raises(AppError) as exc_info:
        derive_annual_income_from_vat(Decimal("1000"), vat_rate=Decimal("0"))
    assert exc_info.value.code == "ADVANCE_PAYMENT.RATE_INVALID"


def test_list_payments_filters_by_status(test_db):
    business = _business(test_db)
    service = AdvancePaymentService(test_db)

    first = service.create_payment_for_client(
        client_record_id=business.client_record_id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100"),
    )
    second = service.create_payment_for_client(
        client_record_id=business.client_record_id,
        period="2026-02",
        period_months_count=1,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("200"),
    )
    service.update_payment_for_client(
        business.client_record_id,
        second.id,
        status=AdvancePaymentStatus.PAID,
        paid_amount=Decimal("200"),
    )

    all_items, total = service.list_payments_for_client(business.client_record_id, year=2026)
    assert total == 2
    assert [p.id for p in all_items] == [first.id, second.id]

    paid_items, paid_total = service.list_payments_for_client(
        business.client_record_id,
        year=2026,
        status=[AdvancePaymentStatus.PAID],
    )
    assert paid_total == 1
    assert paid_items[0].id == second.id
