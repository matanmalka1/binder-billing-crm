from datetime import date

from app.clients.models import Client, ClientType
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository


def _create_client(test_db) -> Client:
    client = Client(
        full_name="Advance Delete Client",
        id_number="ADV-DEL-001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_delete_advance_payment_success(client, test_db, advisor_headers):
    crm_client = _create_client(test_db)
    repo = AdvancePaymentRepository(test_db)
    payment = repo.create(
        client_id=crm_client.id,
        year=2026,
        month=4,
        due_date=date(2026, 5, 15),
    )

    resp = client.delete(f"/api/v1/advance-payments/{payment.id}", headers=advisor_headers)

    assert resp.status_code == 204
    assert repo.get_by_id(payment.id) is None


def test_delete_advance_payment_not_found(client, advisor_headers):
    resp = client.delete("/api/v1/advance-payments/999999", headers=advisor_headers)

    assert resp.status_code == 404
    assert resp.json()["error"] == "ADVANCE_PAYMENT.NOT_FOUND"
