from datetime import date
from io import BytesIO

from app.clients.models import Client, ClientType


def _create_client(test_db) -> Client:
    client = Client(
        full_name="API Test Client",
        id_number="000000002",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_secretary_can_upload_documents(client, secretary_headers, test_db):
    """Test that secretary can upload permanent documents."""
    c = _create_client(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        headers=secretary_headers,
        data={
            "client_id": c.id,
            "document_type": "id_copy",
        },
        files={"file": ("test.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["client_id"] == c.id
    assert data["document_type"] == "id_copy"
    assert data["is_present"] is True


def test_advisor_can_upload_documents(client, advisor_headers, test_db):
    """Test that advisor can upload permanent documents."""
    c = _create_client(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        headers=advisor_headers,
        data={
            "client_id": c.id,
            "document_type": "power_of_attorney",
        },
        files={"file": ("poa.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 201


def test_unauthenticated_cannot_upload_documents(client, test_db):
    """Test that unauthenticated users cannot upload documents."""
    c = _create_client(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        data={
            "client_id": c.id,
            "document_type": "id_copy",
        },
        files={"file": ("test.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 401


def test_invalid_token_cannot_upload_documents(client, test_db):
    """Test that invalid token cannot upload documents."""
    c = _create_client(test_db)

    response = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": "Bearer invalid-token"},
        data={
            "client_id": c.id,
            "document_type": "id_copy",
        },
        files={"file": ("test.pdf", BytesIO(b"fake content"), "application/pdf")},
    )

    assert response.status_code == 401


def test_secretary_can_view_operational_signals(client, secretary_headers, test_db):
    """Test that secretary can view operational signals."""
    c = _create_client(test_db)

    response = client.get(
        f"/api/v1/documents/client/{c.id}/signals",
        headers=secretary_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == c.id
    assert "missing_documents" in data
    assert "binders_nearing_sla" in data
    assert "binders_overdue" in data


def test_advisor_can_view_operational_signals(client, advisor_headers, test_db):
    """Test that advisor can view operational signals."""
    c = _create_client(test_db)

    response = client.get(
        f"/api/v1/documents/client/{c.id}/signals",
        headers=advisor_headers,
    )

    assert response.status_code == 200
