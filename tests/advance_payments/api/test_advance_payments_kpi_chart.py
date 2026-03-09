from datetime import date
from decimal import Decimal

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.clients.models import Client, ClientType


def _client(db) -> Client:
    client = Client(
        full_name="AP KPI Client",
        id_number="APKPI-1",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _seed_payments(db, client_id: int):
    repo = AdvancePaymentRepository(db)
    jan = repo.create(
        client_id=client_id,
        year=2026,
        month=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100"),
    )
    repo.update(jan, paid_amount=Decimal("80"), status=AdvancePaymentStatus.PAID)

    mar = repo.create(
        client_id=client_id,
        year=2026,
        month=3,
        due_date=date(2026, 4, 15),
        expected_amount=Decimal("50"),
    )
    repo.update(mar, paid_amount=Decimal("0"), status=AdvancePaymentStatus.OVERDUE)


def test_chart_endpoint_returns_12_months(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    _seed_payments(test_db, crm_client.id)

    resp = client.get(
        f"/api/v1/advance-payments/chart?client_id={crm_client.id}&year=2026",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["client_id"] == crm_client.id
    assert body["year"] == 2026
    months = body["months"]
    assert len(months) == 12
    month1 = next(m for m in months if m["month"] == 1)
    assert month1["expected_amount"] == 100.0
    assert month1["paid_amount"] == 80.0
    month3 = next(m for m in months if m["month"] == 3)
    assert month3["expected_amount"] == 50.0
    assert month3["overdue_amount"] == 50.0


def test_kpi_endpoint_returns_collection_rate(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    _seed_payments(test_db, crm_client.id)

    resp = client.get(
        f"/api/v1/advance-payments/kpi?client_id={crm_client.id}&year=2026",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == crm_client.id
    assert data["year"] == 2026
    assert data["total_expected"] == 150.0
    assert data["total_paid"] == 80.0
    assert data["collection_rate"] == round(80 / 150 * 100, 2)
    assert data["overdue_count"] >= 1
