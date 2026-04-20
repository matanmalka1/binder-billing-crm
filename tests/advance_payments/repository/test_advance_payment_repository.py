from datetime import date
from decimal import Decimal
from itertools import count

from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    AdvancePaymentAggregationRepository,
)
from app.advance_payments.repositories.advance_payment_repository import (
    AdvancePaymentRepository,
    advance_payment_status_text_expr,
)
from app.businesses.models.business import Business
from app.common.enums import VatType
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository


_seq = count(1)


def _create_user(test_db):
    user = User(
        full_name="Creator",
        email=f"creator{next(_seq)}@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _create_business(test_db, name: str, id_number: str):
    legal_entity = LegalEntity(id_number_type=IdNumberType.INDIVIDUAL, id_number=id_number, official_name=id_number)
    test_db.add(legal_entity)
    test_db.commit()
    test_db.refresh(legal_entity)

    client = Client(full_name=name, id_number=id_number)
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    business = Business(
        client_id=client.id,
        legal_entity_id=legal_entity.id,
        business_name=f"{name} Business",
        opened_at=date(2024, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    business.client_record_id = client.id
    return business


def test_list_by_client_record_year_filters_and_orders(test_db):
    repo = AdvancePaymentRepository(test_db)
    business = _create_business(test_db, "Client One", "100000001")

    january = repo.create(
        client_record_id=business.client_record_id,
        period="2025-01",
        period_months_count=1,
        due_date=date(2025, 2, 15),
        expected_amount=Decimal("100.00"),
    )
    february = repo.create(
        client_record_id=business.client_record_id,
        period="2025-02",
        period_months_count=1,
        due_date=date(2025, 3, 15),
        expected_amount=Decimal("200.00"),
    )
    repo.update(february, status=AdvancePaymentStatus.PAID)

    items, total = repo.list_by_client_record_year(client_record_id=business.client_record_id, year=2025, status=None)
    assert total == 2
    assert [p.period for p in items] == ["2025-01", "2025-02"]

    pending_items, pending_total = repo.list_by_client_record_year(
        client_record_id=business.client_record_id,
        year=2025,
        status=[AdvancePaymentStatus.PENDING],
    )
    assert pending_total == 1
    assert pending_items[0].id == january.id


def test_get_annual_output_vat_returns_sum_or_none(test_db):
    repo = VatClientSummaryRepository(test_db)
    business = _create_business(test_db, "VAT Client", "100000002")
    user = _create_user(test_db)

    january = VatWorkItem(
        client_record_id=business.client_record_id,
        created_by=user.id,
        period="2025-01",
        period_type=VatType.MONTHLY,
        total_output_vat=Decimal("150.50"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("150.50"),
    )
    february = VatWorkItem(
        client_record_id=business.client_record_id,
        created_by=user.id,
        period="2025-02",
        period_type=VatType.MONTHLY,
        total_output_vat=Decimal("149.50"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("149.50"),
    )
    previous_year = VatWorkItem(
        client_record_id=business.client_record_id,
        created_by=user.id,
        period="2024-12",
        period_type=VatType.MONTHLY,
        total_output_vat=Decimal("999.00"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("999.00"),
    )
    test_db.add_all([january, february, previous_year])
    test_db.commit()

    assert repo.get_annual_output_vat(client_record_id=business.client_record_id, year=2025) == Decimal("300.00")


def test_list_overview_payments_filters_by_month_and_status(test_db):
    repo = AdvancePaymentRepository(test_db)
    aggregation_repo = AdvancePaymentAggregationRepository(test_db)
    business_a = _create_business(test_db, "Alpha", "100000003")
    business_b = _create_business(test_db, "Beta", "100000004")

    payment_a = repo.create(
        client_record_id=business_a.client_record_id,
        period="2025-01",
        period_months_count=1,
        due_date=date(2025, 2, 10),
    )
    payment_b = repo.create(
        client_record_id=business_b.client_record_id,
        period="2025-01",
        period_months_count=1,
        due_date=date(2025, 2, 12),
    )
    repo.update(payment_b, status=AdvancePaymentStatus.PAID)

    repo.create(
        client_record_id=business_a.client_record_id,
        period="2025-02",
        period_months_count=1,
        due_date=date(2025, 3, 10),
    )

    rows = aggregation_repo.list_overview_payments(
        year=2025,
        month=1,
        statuses=[AdvancePaymentStatus.PENDING, AdvancePaymentStatus.PAID],
    )

    assert len(rows) == 2
    ids = {r.id for r in rows}
    assert payment_a.id in ids
    assert payment_b.id in ids


def test_list_by_client_record_year_handles_legacy_uppercase_status_values(test_db):
    repo = AdvancePaymentRepository(test_db)
    business = _create_business(test_db, "Legacy Client", "100000005")

    payment = repo.create(
        client_record_id=business.client_record_id,
        period="2026-03",
        period_months_count=1,
        due_date=date(2026, 4, 15),
        expected_amount=Decimal("300.00"),
        paid_amount=Decimal("100.00"),
    )

    test_db.execute(
        text("UPDATE advance_payments SET status = 'PARTIAL' WHERE id = :payment_id"),
        {"payment_id": payment.id},
    )
    test_db.commit()

    items, total = repo.list_by_client_record_year(client_record_id=business.client_record_id, year=2026, status=None)
    assert total == 1
    assert items[0].status == AdvancePaymentStatus.PARTIAL

    filtered, filtered_total = repo.list_by_client_record_year(
        client_record_id=business.client_record_id,
        year=2026,
        status=[AdvancePaymentStatus.PARTIAL],
    )
    assert filtered_total == 1
    assert filtered[0].id == payment.id


def test_status_expression_casts_enum_for_postgres():
    compiled = str(
        advance_payment_status_text_expr().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert compiled == "lower(CAST(advance_payments.status AS VARCHAR))"
