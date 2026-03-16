from datetime import date
from decimal import Decimal

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_analytics_repository import AdvancePaymentAnalyticsRepository
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.clients.models.client import Client, ClientType


def _client(test_db) -> Client:
    c = Client(
        full_name="Advance Repo Missing Client",
        id_number="AP-MISS-1",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def test_advance_payment_get_by_id_and_delete(test_db):
    repo = AdvancePaymentRepository(test_db)
    client = _client(test_db)

    payment = repo.create(
        client_id=client.id,
        year=2026,
        month=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100.00"),
    )

    fetched = repo.get_by_id(payment.id)
    assert fetched is not None
    assert fetched.id == payment.id

    repo.delete(payment)
    assert repo.get_by_id(payment.id) is None


def test_advance_payment_analytics_annual_kpis_and_monthly_chart(test_db):
    repo = AdvancePaymentRepository(test_db)
    analytics = AdvancePaymentAnalyticsRepository(test_db)
    client = _client(test_db)

    jan = repo.create(
        client_id=client.id,
        year=2026,
        month=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100.00"),
    )
    repo.update(jan, paid_amount=Decimal("100.00"), status=AdvancePaymentStatus.PAID)

    feb = repo.create(
        client_id=client.id,
        year=2026,
        month=2,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("200.00"),
    )
    repo.update(feb, paid_amount=Decimal("0.00"), status=AdvancePaymentStatus.OVERDUE)

    kpis = analytics.get_annual_kpis(client.id, 2026)
    assert kpis["total_expected"] == 300.0
    assert kpis["total_paid"] == 100.0
    assert kpis["overdue_count"] == 1
    assert kpis["on_time_count"] == 1

    monthly = analytics.monthly_chart_data(client.id, 2026)
    assert len(monthly) == 12
    assert monthly[0]["month"] == 1
    assert monthly[0]["expected_amount"] == 100.0
    assert monthly[0]["paid_amount"] == 100.0
    assert monthly[1]["overdue_amount"] == 200.0
