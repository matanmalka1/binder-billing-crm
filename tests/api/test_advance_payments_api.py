from datetime import date

from app.models import Client, ClientType
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository


def _create_client(test_db) -> Client:
    client = Client(
        full_name="Advance Payment Client",
        id_number="444444444",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_list_advance_payments_paginates(client, test_db, advisor_headers):
    adv_client = _create_client(test_db)
    repo = AdvancePaymentRepository(test_db)
    repo.create(client_id=adv_client.id, year=2026, month=1, due_date=date(2026, 2, 15))
    repo.create(client_id=adv_client.id, year=2026, month=2, due_date=date(2026, 3, 15))
    repo.create(client_id=adv_client.id, year=2026, month=3, due_date=date(2026, 4, 15))
    # Extra year entry should be filtered out
    repo.create(client_id=adv_client.id, year=2025, month=12, due_date=date(2026, 1, 15))

    response = client.get(
        f"/api/v1/advance-payments?client_id={adv_client.id}&year=2026&page=1&page_size=2",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert [item["month"] for item in data["items"]] == [1, 2]

    second_page = client.get(
        f"/api/v1/advance-payments?client_id={adv_client.id}&year=2026&page=2&page_size=2",
        headers=advisor_headers,
    )
    assert second_page.status_code == 200
    assert [item["month"] for item in second_page.json()["items"]] == [3]


def test_update_advance_payment_success(client, test_db, advisor_headers):
    adv_client = _create_client(test_db)
    repo = AdvancePaymentRepository(test_db)
    payment = repo.create(
        client_id=adv_client.id,
        year=2026,
        month=5,
        due_date=date(2026, 6, 15),
        expected_amount=500.0,
    )

    response = client.patch(
        f"/api/v1/advance-payments/{payment.id}",
        headers=advisor_headers,
        json={"paid_amount": 500.0, "status": "paid"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paid"
    assert data["paid_amount"] == 500.0
    assert data["updated_at"] is not None


def test_update_advance_payment_invalid_status_returns_400(client, test_db, advisor_headers):
    adv_client = _create_client(test_db)
    repo = AdvancePaymentRepository(test_db)
    payment = repo.create(
        client_id=adv_client.id,
        year=2026,
        month=7,
        due_date=date(2026, 8, 15),
    )

    response = client.patch(
        f"/api/v1/advance-payments/{payment.id}",
        headers=advisor_headers,
        json={"status": "unknown"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid status: unknown"


def test_update_advance_payment_not_found_returns_404(client, advisor_headers):
    response = client.patch(
        "/api/v1/advance-payments/999",
        headers=advisor_headers,
        json={"status": "paid"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Advance payment 999 not found"


def test_list_advance_payments_missing_client_returns_404(client, advisor_headers):
    response = client.get(
        "/api/v1/advance-payments?client_id=999&year=2026",
        headers=advisor_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"
