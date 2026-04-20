from datetime import date

from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType


def _create_business(test_db) -> Business:
    legal_entity = LegalEntity(id_number_type=IdNumberType.INDIVIDUAL, id_number="ADV-DEL-001", official_name="ADV-DEL-001")
    test_db.add(legal_entity)
    test_db.commit()
    test_db.refresh(legal_entity)

    client = Client(full_name="Advance Delete Client", id_number="ADV-DEL-001")
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    business = Business(
        client_id=client.id,
        legal_entity_id=legal_entity.id,
        business_name="Advance Delete Business",
        opened_at=date.today(),
    )
    test_db.add(business)
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
