from app.clients.models.client import Client


def test_binder_receive_creates_in_office_binder(client, advisor_headers, test_db):
    """Regression: binder receive still creates IN_OFFICE binder."""
    test_client = Client(
        full_name="S5 Regression Client",
        id_number="555555550",
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    response = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_id": test_client.id,
            "binder_number": "S5-REG-001",
            "period_start": "2026-01-01",
            "binder_type": "other",
            "received_at": "2026-02-09",
            "received_by": 1,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["binder"]["binder_number"].startswith(str(test_client.id) + "/")
    assert data["binder"]["status"] == "in_office"


def test_open_binders_endpoint_returns_items(client, advisor_headers):
    """Regression: open binders endpoint still returns items."""
    response = client.get("/api/v1/binders/open", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()


def test_charges_endpoint_creates_draft_charge(client, advisor_headers, test_db):
    """Regression: charge creation still returns draft status."""
    test_client = Client(
        full_name="S5 Billing Client",
        id_number="555555551",
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "business_id": test_client.id,
            "amount": 100.0,
            "charge_type": "other",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"


def test_document_signals_endpoint_lists_missing_documents(client, advisor_headers, secretary_headers, test_db):
    """Regression: document signals still list missing documents."""
    test_client = Client(
        full_name="S5 Notification Client",
        id_number="555555552",
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    response = client.get(
        f"/api/v1/documents/business/{test_client.id}/signals",
        headers=secretary_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "missing_documents" in data
