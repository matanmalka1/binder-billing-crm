from datetime import date, datetime

from app.businesses.models.business import Business, EntityType
from app.clients.models.client import Client
from app.correspondence.models.correspondence import CorrespondenceType
from app.correspondence.services.correspondence_service import CorrespondenceService


def _create_business(test_db, id_number: str = "111222333") -> Business:
    client = Client(
        full_name="Update Test Client",
        id_number=id_number,
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Update Business {id_number}",
        entity_type=EntityType.COMPANY_LTD,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def _add_entry(test_db, business_id: int, user_id: int):
    svc = CorrespondenceService(test_db)
    return svc.add_entry(
        business_id=business_id,
        correspondence_type=CorrespondenceType.EMAIL,
        subject="Original subject",
        occurred_at=datetime(2026, 1, 10, 9, 0, 0),
        created_by=user_id,
    )


def test_update_correspondence(client, test_db, advisor_headers, test_user):
    business = _create_business(test_db)
    entry = _add_entry(test_db, business.id, test_user.id)

    response = client.patch(
        f"/api/v1/businesses/{business.id}/correspondence/{entry.id}",
        headers=advisor_headers,
        json={"subject": "Updated subject", "correspondence_type": "meeting"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "Updated subject"
    assert data["correspondence_type"] == "meeting"
    assert data["occurred_at"].startswith("2026-01-10")


def test_update_correspondence_invalid_type(client, test_db, advisor_headers, test_user):
    business = _create_business(test_db)
    entry = _add_entry(test_db, business.id, test_user.id)

    response = client.patch(
        f"/api/v1/businesses/{business.id}/correspondence/{entry.id}",
        headers=advisor_headers,
        json={"correspondence_type": "invalid_type"},
    )

    assert response.status_code == 422


def test_update_correspondence_not_found(client, test_db, advisor_headers):
    business = _create_business(test_db)

    response = client.patch(
        f"/api/v1/businesses/{business.id}/correspondence/99999",
        headers=advisor_headers,
        json={"subject": "x"},
    )

    assert response.status_code == 404


def test_delete_correspondence(client, test_db, advisor_headers, test_user):
    business = _create_business(test_db)
    entry = _add_entry(test_db, business.id, test_user.id)

    response = client.delete(
        f"/api/v1/businesses/{business.id}/correspondence/{entry.id}",
        headers=advisor_headers,
    )

    assert response.status_code == 204


def test_deleted_not_returned_in_list(client, test_db, advisor_headers, test_user):
    business = _create_business(test_db)
    entry = _add_entry(test_db, business.id, test_user.id)

    client.delete(
        f"/api/v1/businesses/{business.id}/correspondence/{entry.id}",
        headers=advisor_headers,
    )

    response = client.get(
        f"/api/v1/businesses/{business.id}/correspondence",
        headers=advisor_headers,
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert entry.id not in ids


def test_delete_correspondence_secretary_forbidden(
    client, test_db, secretary_headers, test_user
):
    business = _create_business(test_db)
    entry = _add_entry(test_db, business.id, test_user.id)

    response = client.delete(
        f"/api/v1/businesses/{business.id}/correspondence/{entry.id}",
        headers=secretary_headers,
    )

    assert response.status_code == 403
