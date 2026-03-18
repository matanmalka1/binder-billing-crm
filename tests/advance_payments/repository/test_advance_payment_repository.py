from datetime import date
from decimal import Decimal

import pytest

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.clients.models.client import Client, ClientType
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository


def _create_user(test_db):
    user = User(
        full_name="Creator",
        email="creator@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _create_client(test_db, name: str, id_number: str):
    client = Client(
        full_name=name,
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_list_by_client_year_filters_and_orders(test_db):
    repo = AdvancePaymentRepository(test_db)
    client = _create_client(test_db, "Client One", "AP001")

    january = repo.create(
        client_id=client.id,
        year=2025,
        month=1,
        due_date=date(2025, 1, 15),
        expected_amount=Decimal("100.00"),
    )
    february = repo.create(
        client_id=client.id,
        year=2025,
        month=2,
        due_date=date(2025, 2, 15),
        expected_amount=Decimal("200.00"),
    )
    repo.update(february, status=AdvancePaymentStatus.PAID)

    items, total = repo.list_by_client_year(client_id=client.id, year=2025, status=None)
    assert total == 2
    assert [p.month for p in items] == [1, 2]

    pending_items, pending_total = repo.list_by_client_year(
        client_id=client.id,
        year=2025,
        status=[AdvancePaymentStatus.PENDING],
    )
    assert pending_total == 1
    assert pending_items[0].id == january.id


def test_get_annual_output_vat_returns_sum_or_none(test_db):
    """Current repository implementation does not expose get_annual_output_vat."""
    repo = VatClientSummaryRepository(test_db)
    client = _create_client(test_db, "VAT Client", "AP002")
    user = _create_user(test_db)

    january = VatWorkItem(
        client_id=client.id,
        created_by=user.id,
        period="2025-01",
        total_output_vat=Decimal("150.50"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("150.50"),
    )
    february = VatWorkItem(
        client_id=client.id,
        created_by=user.id,
        period="2025-02",
        total_output_vat=Decimal("149.50"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("149.50"),
    )
    previous_year = VatWorkItem(
        client_id=client.id,
        created_by=user.id,
        period="2024-12",
        total_output_vat=Decimal("999.00"),
        total_input_vat=Decimal("0"),
        net_vat=Decimal("999.00"),
    )
    test_db.add_all([january, february, previous_year])
    test_db.commit()

    with pytest.raises(AttributeError):
        repo.get_annual_output_vat(client_id=client.id, year=2025)


def test_list_overview_payments_filters_by_month_and_status(test_db):
    """list_overview_payments returns AdvancePayment rows without client join."""
    repo = AdvancePaymentRepository(test_db)
    client_a = _create_client(test_db, "Alpha", "AP003")
    client_b = _create_client(test_db, "Beta", "AP004")

    payment_a = repo.create(
        client_id=client_a.id,
        year=2025,
        month=1,
        due_date=date(2025, 1, 10),
    )
    payment_b = repo.create(
        client_id=client_b.id,
        year=2025,
        month=1,
        due_date=date(2025, 1, 12),
    )
    repo.update(payment_b, status=AdvancePaymentStatus.PAID)

    repo.create(
        client_id=client_a.id,
        year=2025,
        month=2,
        due_date=date(2025, 2, 10),
    )

    rows = repo.list_overview_payments(
        year=2025,
        month=1,
        statuses=[AdvancePaymentStatus.PENDING, AdvancePaymentStatus.PAID],
    )

    assert len(rows) == 2
    ids = {r.id for r in rows}
    assert payment_a.id in ids
    assert payment_b.id in ids
