"""
Tests for POST/GET /api/v1/clients.
Uses valid Israeli ID numbers (pass Luhn checksum).
Valid test IDs: 039337423, 087654321 (verified below), use id_number_type=corporation to bypass checksum for convenience.
"""

from app.businesses.models.business import Business
from app.clients.models.client import Client


class _CreateResponse:
    def __init__(self, response):
        self._response = response
        self.status_code = response.status_code

    def json(self):
        payload = self._response.json()
        return payload["client"] if self.status_code == 201 else payload


def _create_client(client, headers, full_name="Test Client", id_number="000000000"):
    """Helper: create a client with an initial business."""
    resp = client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "client": {
                "full_name": full_name,
                "id_number": id_number,
                "id_number_type": "corporation",
            },
            "business": {"business_name": f"{full_name} Business"},
        },
    )
    return _CreateResponse(resp)


def test_authenticated_client_creation(client, auth_token):
    """Authenticated user can create a client."""
    response = _create_client(
        client,
        {"Authorization": f"Bearer {auth_token}"},
        full_name="John Doe",
        id_number="100000009",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "John Doe"
    assert data["id_number"] == "100000009"
    assert data["id_number_type"] == "corporation"
    assert "id" in data
    assert "created_at" in data
    assert data["created_at"].endswith("Z")


def test_identity_only_client_creation_is_not_available(client, advisor_headers):
    response = client.post(
        "/api/v1/clients",
        headers=advisor_headers,
        json={
            "full_name": "Identity Only",
            "id_number": "LEGACY-001",
            "id_number_type": "other",
        },
    )

    assert response.status_code == 422


def test_client_creation_duplicate_id_number(client, auth_token):
    """Duplicate id_number returns 409."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    _create_client(client, headers, full_name="Jane Doe", id_number="200000008")

    response = _create_client(client, headers, full_name="John Smith", id_number="200000008")

    assert response.status_code == 409
    data = response.json()
    assert data["detail"]["error"] in ("CLIENT.CONFLICT", "CLIENT.DELETED_EXISTS")


def test_clients_list_returns_paginated_response(client, auth_token):
    """List endpoint returns items/page/page_size/total."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    list_response = client.get("/api/v1/clients", headers=headers)

    assert list_response.status_code == 200
    data = list_response.json()
    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "total" in data


def test_create_client_creates_client_and_initial_business(client, test_db, advisor_headers):
    response = client.post(
        "/api/v1/clients",
        headers=advisor_headers,
        json={
            "client": {
                "full_name": "Created Client",
                "id_number": "ONB-001",
                "id_number_type": "other",
                "phone": "050-1234567",
                "email": "created@example.com",
            },
            "business": {
                "business_name": "Created Business",
                "opened_at": "2026-04-19",
            },
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["client"]["full_name"] == "Created Client"
    assert data["business"]["business_name"] == "Created Business"
    assert data["business"]["client_id"] == data["client"]["id"]

    stored_business = (
        test_db.query(Business)
        .filter(
            Business.client_id == data["client"]["id"],
            Business.business_name == "Created Business",
        )
        .one()
    )
    assert stored_business.opened_at.isoformat() == "2026-04-19"


def test_create_client_requires_advisor_role(client, secretary_headers):
    response = client.post(
        "/api/v1/clients",
        headers=secretary_headers,
        json={
            "client": {
                "full_name": "Secretary Create",
                "id_number": "ONB-SEC",
                "id_number_type": "other",
            },
            "business": {"business_name": "Secretary Business"},
        },
    )

    assert response.status_code == 403


def test_create_client_rejects_blank_business_before_creating_client(
    client,
    test_db,
    advisor_headers,
):
    response = client.post(
        "/api/v1/clients",
        headers=advisor_headers,
        json={
            "client": {
                "full_name": "Invalid Create",
                "id_number": "ONB-BLANK",
                "id_number_type": "other",
            },
            "business": {"business_name": "   "},
        },
    )

    assert response.status_code == 422
    assert (
        test_db.query(Client)
        .filter(Client.id_number == "ONB-BLANK")
        .count()
        == 0
    )
