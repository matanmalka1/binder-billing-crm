from datetime import date
from decimal import Decimal
from itertools import count

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.clients.models import Client, ClientType
from app.clients.models.client_tax_profile import ClientTaxProfile
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.models.vat_enums import VatWorkItemStatus


_client_seq = count(1)


def _client(db) -> Client:
    client = Client(
        full_name="Advance Client",
        id_number=f"66666666{next(_client_seq)}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _tax_profile(db, client_id: int, advance_rate: Decimal = Decimal("6.0")) -> ClientTaxProfile:
    profile = ClientTaxProfile(client_id=client_id, advance_rate=advance_rate)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _vat_work_item(db, client_id: int, created_by: int, period: str, output_vat: Decimal):
    item = VatWorkItem(
        client_id=client_id,
        created_by=created_by,
        period=period,
        status=VatWorkItemStatus.FILED,
        total_output_vat=output_vat,
        total_input_vat=Decimal("0"),
        net_vat=output_vat,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_create_advance_payment_and_conflict(client, test_db, advisor_headers):
    crm_client = _client(test_db)

    payload = {
        "client_id": crm_client.id,
        "year": 2026,
        "month": 3,
        "due_date": "2026-04-15",
        "expected_amount": 1200.0,
    }
    first = client.post("/api/v1/advance-payments", headers=advisor_headers, json=payload)
    assert first.status_code == 201
    assert first.json()["month"] == 3

    conflict = client.post("/api/v1/advance-payments", headers=advisor_headers, json=payload)
    data = conflict.json()
    assert conflict.status_code == 409
    assert data["error"]["type"] == "ADVANCE_PAYMENT.CONFLICT"
    assert data["error"]["status_code"] == 409
    assert isinstance(data["error"]["detail"], str)


def test_suggest_expected_amount_uses_vat_and_advance_rate(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    _tax_profile(test_db, crm_client.id, advance_rate=Decimal("6.0"))
    _vat_work_item(test_db, crm_client.id, test_user.id, "2025-01", Decimal("18000"))

    resp = client.get(
        f"/api/v1/advance-payments/suggest?client_id={crm_client.id}&year=2026",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["has_data"] is True
    assert float(body["suggested_amount"]) == 500.0


def test_overview_filters_by_status_and_month(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = AdvancePaymentRepository(test_db)
    jan = repo.create(client_id=crm_client.id, year=2026, month=1, due_date=date(2026, 2, 15))
    feb = repo.create(client_id=crm_client.id, year=2026, month=2, due_date=date(2026, 3, 15))
    repo.update(feb, status=AdvancePaymentStatus.PAID, paid_amount=Decimal("1200"))

    resp = client.get(
        "/api/v1/advance-payments/overview?year=2026&month=2&status=paid&page=1&page_size=10",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["month"] == 2
    assert item["status"] == "paid"
