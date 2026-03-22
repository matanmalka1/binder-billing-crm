from datetime import date
from decimal import Decimal

from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client


def _create_business(test_db) -> Business:
    client = Client(full_name="Advance Payment Client", id_number="444444444")
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name="Advance Payment Business",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_list_advance_payments_paginates(client, test_db, advisor_headers):
    business = _create_business(test_db)
    repo = AdvancePaymentRepository(test_db)
    repo.create(business_id=business.id, period="2026-01", period_months_count=1, due_date=date(2026, 2, 15))
    repo.create(business_id=business.id, period="2026-02", period_months_count=1, due_date=date(2026, 3, 15))
    repo.create(business_id=business.id, period="2026-03", period_months_count=1, due_date=date(2026, 4, 15))
    # Extra year entry should be filtered out
    repo.create(business_id=business.id, period="2025-12", period_months_count=1, due_date=date(2026, 1, 15))

    response = client.get(
        f"/api/v1/businesses/{business.id}/advance-payments?year=2026&page=1&page_size=2",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert [item["period"] for item in data["items"]] == ["2026-01", "2026-02"]

    second_page = client.get(
        f"/api/v1/businesses/{business.id}/advance-payments?year=2026&page=2&page_size=2",
        headers=advisor_headers,
    )
    assert second_page.status_code == 200
    assert [item["period"] for item in second_page.json()["items"]] == ["2026-03"]


def test_update_advance_payment_success(client, test_db, advisor_headers):
    business = _create_business(test_db)
    repo = AdvancePaymentRepository(test_db)
    payment = repo.create(
        business_id=business.id,
        period="2026-05",
        period_months_count=1,
        due_date=date(2026, 6, 15),
        expected_amount=500.0,
    )

    response = client.patch(
        f"/api/v1/businesses/{business.id}/advance-payments/{payment.id}",
        headers=advisor_headers,
        json={"paid_amount": 500.0, "status": "paid"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paid"
    assert Decimal(str(data["paid_amount"])) == Decimal("500.00")
    assert data["updated_at"] is not None


def test_update_advance_payment_invalid_status_returns_400(client, test_db, advisor_headers):
    business = _create_business(test_db)
    repo = AdvancePaymentRepository(test_db)
    payment = repo.create(
        business_id=business.id,
        period="2026-07",
        period_months_count=1,
        due_date=date(2026, 8, 15),
    )

    response = client.patch(
        f"/api/v1/businesses/{business.id}/advance-payments/{payment.id}",
        headers=advisor_headers,
        json={"status": "unknown"},
    )

    assert response.status_code == 422


def test_update_advance_payment_not_found_returns_404(client, test_db, advisor_headers):
    business = _create_business(test_db)
    response = client.patch(
        f"/api/v1/businesses/{business.id}/advance-payments/999",
        headers=advisor_headers,
        json={"status": "paid"},
    )

    data = response.json()
    assert response.status_code == 404
    assert data["error"] == "ADVANCE_PAYMENT.NOT_FOUND"
    assert data["error_meta"]["status_code"] == 404
    assert isinstance(data["error_meta"]["detail"], str)


def test_list_advance_payments_missing_business_returns_404(client, advisor_headers):
    response = client.get(
        "/api/v1/businesses/999/advance-payments?year=2026",
        headers=advisor_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND"
    assert data["error_meta"]["detail"] == "עסק 999 לא נמצא"
