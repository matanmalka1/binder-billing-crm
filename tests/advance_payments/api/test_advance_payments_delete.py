from datetime import date

from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.businesses.models.business import Business
from tests.helpers.identity import seed_business, seed_client_identity


def _create_business(test_db) -> Business:
    client = seed_client_identity(
        test_db,
        full_name="Advance Delete Client",
        id_number="ADV-DEL-001",
    )
    business = seed_business(
        test_db,
        legal_entity_id=client.legal_entity_id,
        business_name="Advance Delete Business",
        opened_at=date.today(),
    )
    test_db.commit()
    test_db.refresh(business)
    business.client_record_id = client.id
    return business


def test_delete_advance_payment_success(client, test_db, advisor_headers):
    business = _create_business(test_db)
    repo = AdvancePaymentRepository(test_db)
    payment = repo.create(
        client_record_id=business.client_record_id,
        period="2026-04",
        period_months_count=1,
        due_date=date(2026, 5, 15),
    )

    resp = client.delete(
        f"/api/v1/clients/{business.client_record_id}/advance-payments/{payment.id}",
        headers=advisor_headers,
    )

    assert resp.status_code == 204
    assert repo.get_by_id(payment.id) is None


def test_delete_advance_payment_not_found(client, test_db, advisor_headers):
    business = _create_business(test_db)
    resp = client.delete(
        f"/api/v1/clients/{business.client_record_id}/advance-payments/999999",
        headers=advisor_headers,
    )

    assert resp.status_code == 404
    assert resp.json()["error"] == "ADVANCE_PAYMENT.NOT_FOUND"
