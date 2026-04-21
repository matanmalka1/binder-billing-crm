from datetime import date
from decimal import Decimal
from itertools import count

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.businesses.models.business import Business
from app.common.enums import VatType
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from tests.helpers.identity import seed_business, seed_client_identity


_client_seq = count(1)


def _business(db):
    id_number = f"66666666{next(_client_seq)}"
    client = seed_client_identity(db, full_name="Advance Client", id_number=id_number)
    business = seed_business(
        db,
        legal_entity_id=client.legal_entity_id,
        business_name="Advance Overview Business",
        opened_at=date.today(),
    )
    db.commit()
    db.refresh(business)
    business.client_record_id = client.id
    return business


def _tax_profile(db, business_id: int, advance_rate: Decimal = Decimal("6.0")) -> None:
    business = db.get(Business, business_id)
    assert business is not None
    business.legal_entity.advance_rate = advance_rate
    db.commit()


def _vat_work_item(db, business_id: int, created_by: int, period: str, output_vat: Decimal):
    business = db.get(Business, business_id)
    assert business is not None
    item = VatWorkItem(
        client_record_id=business.client_record_id,
        created_by=created_by,
        period=period,
        period_type=VatType.MONTHLY,
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
    business = _business(test_db)

    payload = {
        "period": "2026-03",
        "period_months_count": 1,
        "due_date": "2026-04-15",
        "expected_amount": 1200.0,
    }
    first = client.post(
        f"/api/v1/clients/{business.client_record_id}/advance-payments",
        headers=advisor_headers,
        json=payload,
    )
    assert first.status_code == 201
    assert first.json()["period"] == "2026-03"

    conflict = client.post(
        f"/api/v1/clients/{business.client_record_id}/advance-payments",
        headers=advisor_headers,
        json=payload,
    )
    data = conflict.json()
    assert conflict.status_code == 409
    assert data["error"] == "ADVANCE_PAYMENT.CONFLICT"
    assert data["error_meta"]["status_code"] == 409
    assert isinstance(data["error_meta"]["detail"], str)


def test_suggest_expected_amount_uses_vat_and_advance_rate(client, test_db, advisor_headers, test_user):
    business = _business(test_db)
    _tax_profile(test_db, business.id, advance_rate=Decimal("6.0"))
    _vat_work_item(test_db, business.id, test_user.id, "2025-01", Decimal("18000"))

    resp = client.get(
        f"/api/v1/clients/{business.client_record_id}/advance-payments/suggest?year=2026",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["client_record_id"] == business.client_record_id
    assert data["year"] == 2026
    assert data["has_data"] is True
    assert Decimal(str(data["suggested_amount"])) == Decimal("500")


def test_overview_filters_by_status_and_month(client, test_db, advisor_headers):
    business = _business(test_db)
    repo = AdvancePaymentRepository(test_db)
    repo.create(client_record_id=business.client_record_id, period="2026-01", period_months_count=1, due_date=date(2026, 2, 15))
    feb = repo.create(client_record_id=business.client_record_id, period="2026-02", period_months_count=1, due_date=date(2026, 3, 15))
    repo.update(feb, status=AdvancePaymentStatus.PAID, paid_amount=Decimal("1200"))

    resp = client.get(
        "/api/v1/advance-payments/overview?year=2026&month=2&status=paid&page=1&page_size=10",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["period"] == "2026-02"
    assert item["status"] == "paid"
