from datetime import date
from decimal import Decimal
from itertools import count

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_analytics_repository import AdvancePaymentAnalyticsRepository
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType


_seq = count(1)


def _business(test_db) -> Business:
    idx = next(_seq)
    legal_entity = LegalEntity(id_number_type=IdNumberType.INDIVIDUAL, id_number=f"100001{idx:03d}", official_name=f"100001{idx:03d}")
    test_db.add(legal_entity)
    test_db.commit()
    test_db.refresh(legal_entity)

    client = Client(
        full_name="Advance Repo Missing Client",
        id_number=legal_entity.id_number,
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    business = Business(
        legal_entity_id=legal_entity.id,
        business_name="Advance Repo Missing Business",
        opened_at=date(2024, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    business.client_record_id = client.id
    return business


def test_advance_payment_get_by_id_for_client_and_soft_delete(test_db):
    repo = AdvancePaymentRepository(test_db)
    business = _business(test_db)

    payment = repo.create(
        client_record_id=business.client_record_id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100.00"),
    )

    fetched = repo.get_by_id_for_client_record(payment.id, business.client_record_id)
    assert fetched is not None
    assert fetched.id == payment.id

    assert repo.soft_delete(payment.id, deleted_by=123) is True
    assert repo.get_by_id(payment.id) is None


def test_advance_payment_exists_for_period_and_sum_paid(test_db):
    repo = AdvancePaymentRepository(test_db)
    business = _business(test_db)

    jan = repo.create(
        client_record_id=business.client_record_id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100.00"),
    )
    repo.update(jan, paid_amount=Decimal("100.00"), status=AdvancePaymentStatus.PAID)

    feb = repo.create(
        client_record_id=business.client_record_id,
        period="2026-02",
        period_months_count=1,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("200.00"),
    )
    repo.update(feb, paid_amount=Decimal("150.00"), status=AdvancePaymentStatus.PARTIAL)

    assert repo.exists_for_period(business.client_record_id, "2026-01") is True
    assert repo.exists_for_period(business.client_record_id, "2026-03") is False
    assert repo.sum_paid_by_client_year(business.client_record_id, 2026) == 100.0


def test_advance_payment_analytics_annual_kpis_and_monthly_chart(test_db):
    repo = AdvancePaymentRepository(test_db)
    analytics = AdvancePaymentAnalyticsRepository(test_db)
    business = _business(test_db)

    jan = repo.create(
        client_record_id=business.client_record_id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100.00"),
    )
    repo.update(jan, paid_amount=Decimal("100.00"), status=AdvancePaymentStatus.PAID)

    feb = repo.create(
        client_record_id=business.client_record_id,
        period="2026-02",
        period_months_count=1,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("200.00"),
    )
    repo.update(feb, paid_amount=Decimal("0.00"), status=AdvancePaymentStatus.OVERDUE)

    kpis = analytics.get_annual_kpis_for_client(business.client_record_id, 2026)
    assert kpis["total_expected"] == 300.0
    assert kpis["total_paid"] == 100.0
    assert kpis["overdue_count"] == 1
    assert kpis["on_time_count"] == 1

    monthly = analytics.monthly_chart_data_for_client(business.client_record_id, 2026)
    assert len(monthly) == 2
    assert monthly[0]["period"] == "2026-01"
    assert monthly[0]["expected_amount"] == 100.0
    assert monthly[0]["paid_amount"] == 100.0
    assert monthly[1]["overdue_amount"] == 200.0
