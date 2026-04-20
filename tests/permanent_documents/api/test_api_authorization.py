from datetime import date
from io import BytesIO

from app.businesses.models.business import Business
from app.clients.models.client import Client, IdNumberType
from app.clients.repositories.client_record_repository import ClientRecordRepository


def _create_business(test_db) -> Business:
    client = Client(
        full_name="API Test Client",
        id_number="71080001",
        id_number_type=IdNumberType.CORPORATION,
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    client_record = ClientRecordRepository(test_db).get_by_client_id(client.id)

    business = Business(
        client_id=client.id,
        legal_entity_id=client_record.legal_entity_id,
        business_name="API Test Biz",
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_secretary_can_upload_documents(client, secretary_headers, test_db):
    """Test that secretary can upload permanent documents."""
    b = _create_business(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        headers=secretary_headers,
        data={
            "client_id": b.client_id,
            "business_id": b.id,
            "document_type": "id_copy",
        },
        files={"file": ("test.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["client_id"] == b.client_id
    assert data["business_id"] == b.id
    assert data["document_type"] == "id_copy"
    assert data["is_present"] is True


def test_advisor_can_upload_documents(client, advisor_headers, test_db):
    """Test that advisor can upload permanent documents."""
    b = _create_business(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        headers=advisor_headers,
        data={
            "client_id": b.client_id,
            "business_id": b.id,
            "document_type": "power_of_attorney",
        },
        files={"file": ("poa.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 201


def test_unauthenticated_cannot_upload_documents(client, test_db):
    """Test that unauthenticated users cannot upload documents."""
    b = _create_business(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        data={
            "client_id": b.client_id,
            "business_id": b.id,
            "document_type": "id_copy",
        },
        files={"file": ("test.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 401


def test_invalid_token_cannot_upload_documents(client, test_db):
    """Test that invalid token cannot upload documents."""
    b = _create_business(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": "Bearer invalid-token"},
        data={
            "client_id": b.client_id,
            "business_id": b.id,
            "document_type": "id_copy",
        },
        files={"file": ("test.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 401


def test_secretary_can_view_operational_signals(client, secretary_headers, test_db):
    """Test that secretary can view operational signals."""
    b = _create_business(test_db)

    response = client.get(
        f"/api/v1/documents/client/{b.client_id}/signals",
        headers=secretary_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == b.client_id
    assert "missing_documents" in data


def test_advisor_can_view_operational_signals(client, advisor_headers, test_db):
    """Test that advisor can view operational signals."""
    b = _create_business(test_db)

    response = client.get(
        f"/api/v1/documents/client/{b.client_id}/signals",
        headers=advisor_headers,
    )

    assert response.status_code == 200
