from datetime import date
from decimal import Decimal

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType


def _business(db) -> Business:
    legal_entity = LegalEntity(id_number_type=IdNumberType.INDIVIDUAL, id_number="APKPI-1")
    db.add(legal_entity)
    db.commit()
    db.refresh(legal_entity)

    crm_client = Client(full_name="AP KPI Client", id_number="APKPI-1")
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    business = Business(
        client_id=crm_client.id,
        legal_entity_id=legal_entity.id,
        business_name="AP KPI Business",
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    business.client_record_id = crm_client.id
    return business


def _seed_payments(db, client_record_id: int):
    repo = AdvancePaymentRepository(db)
    jan = repo.create(
        client_record_id=client_record_id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100"),
    )
    repo.update(jan, paid_amount=Decimal("80"), status=AdvancePaymentStatus.PAID)

    mar = repo.create(
        client_record_id=client_record_id,
        period="2026-03",
        period_months_count=1,
        due_date=date(2026, 4, 15),
        expected_amount=Decimal("50"),
    )
    repo.update(mar, paid_amount=Decimal("0"), status=AdvancePaymentStatus.OVERDUE)


def test_chart_endpoint_returns_12_months(client, test_db, advisor_headers):
    business = _business(test_db)
    _seed_payments(test_db, business.client_record_id)

    resp = client.get(
        f"/api/v1/clients/{business.client_record_id}/advance-payments/chart?year=2026",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["client_record_id"] == business.client_record_id
    assert body["year"] == 2026
    months = body["months"]
    assert len(months) == 2
    month1 = next(m for m in months if m["period"] == "2026-01")
    assert Decimal(str(month1["expected_amount"])) == Decimal("100")
    assert Decimal(str(month1["paid_amount"])) == Decimal("80")
    month3 = next(m for m in months if m["period"] == "2026-03")
    assert Decimal(str(month3["expected_amount"])) == Decimal("50")
    assert Decimal(str(month3["overdue_amount"])) == Decimal("50")


def test_kpi_endpoint_returns_collection_rate(client, test_db, advisor_headers):
    business = _business(test_db)
    _seed_payments(test_db, business.client_record_id)

    resp = client.get(
        f"/api/v1/clients/{business.client_record_id}/advance-payments/kpi?year=2026",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["client_record_id"] == business.client_record_id
    assert data["year"] == 2026
    assert Decimal(str(data["total_expected"])) == Decimal("150")
    assert Decimal(str(data["total_paid"])) == Decimal("80")
    assert data["collection_rate"] == round(80 / 150 * 100, 2)
    assert data["overdue_count"] >= 1
