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
from app.businesses.models.business import Business, BusinessType
from app.businesses.models.business_tax_profile import BusinessTaxProfile, VatType
from app.clients.models.client import Client
from app.core.exceptions import AppError, ConflictError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


_seq = count(1)


def _business(db) -> Business:
    idx = next(_seq)
    client = Client(
        full_name=f"Advance Service Client {idx}",
        id_number=f"777777{idx:03d}",
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Advance Service Business {idx}",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def test_create_payment_duplicate_period_raises_conflict(test_db):
    business = _business(test_db)
    service = AdvancePaymentService(test_db)

    service.create_payment(
        business_id=business.id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
    )

    with pytest.raises(ConflictError):
        service.create_payment(
            business_id=business.id,
            period="2026-01",
            period_months_count=1,
            due_date=date(2026, 2, 15),
        )


def test_suggest_expected_amount_requires_profile_and_vat(test_db, test_user):
    business = _business(test_db)
    service = AdvancePaymentService(test_db)

    assert service.suggest_expected_amount(business.id, 2026) is None

    profile = BusinessTaxProfile(
        business_id=business.id,
        vat_type=VatType.MONTHLY,
        advance_rate=Decimal("6.0"),
    )
    test_db.add(profile)
    test_db.commit()

    assert service.suggest_expected_amount(business.id, 2026) is None

    vat_item = VatWorkItem(
        business_id=business.id,
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

    assert service.suggest_expected_amount(business.id, 2026) == Decimal("500")


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

    first = service.create_payment(
        business_id=business.id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100"),
    )
    second = service.create_payment(
        business_id=business.id,
        period="2026-02",
        period_months_count=1,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("200"),
    )
    service.update_payment(business.id, second.id, status=AdvancePaymentStatus.PAID, paid_amount=Decimal("200"))

    all_items, total = service.list_payments(business.id, year=2026)
    assert total == 2
    assert [p.id for p in all_items] == [first.id, second.id]

    paid_items, paid_total = service.list_payments(
        business.id,
        year=2026,
        status=[AdvancePaymentStatus.PAID],
    )
    assert paid_total == 1
    assert paid_items[0].id == second.id
