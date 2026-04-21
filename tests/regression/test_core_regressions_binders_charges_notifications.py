from tests.helpers.identity import seed_client_identity, seed_client_with_business


def test_binder_receive_creates_in_office_binder(client, advisor_headers, test_db):
    """Regression: binder receive still creates IN_OFFICE binder."""
    test_client = seed_client_identity(
        test_db,
        full_name="S5 Regression Client",
        id_number="555555550",
        office_client_number=501,
    )
    test_db.commit()

    response = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_record_id": test_client.id,
            "received_at": "2026-02-09",
            "received_by": 1,
            "materials": [
                {
                    "material_type": "other",
                    "period_year": 2026,
                    "period_month_start": 1,
                    "period_month_end": 1,
                }
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["binder"]["binder_number"] == "501/1"
    assert data["binder"]["status"] == "in_office"


def test_open_binders_endpoint_returns_items(client, advisor_headers):
    """Regression: open binders endpoint still returns items."""
    response = client.get("/api/v1/binders/open", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()


def test_charges_endpoint_creates_draft_charge(client, advisor_headers, test_db):
    """Regression: charge creation still returns draft status."""
    test_client, business = seed_client_with_business(
        test_db,
        full_name="S5 Billing Client",
        id_number="555555551",
    )
    test_db.commit()

    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "client_record_id": test_client.id,
            "business_id": business.id if business else None,
            "amount": 100.0,
            "charge_type": "other",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"


def test_document_signals_endpoint_lists_missing_documents(client, advisor_headers, secretary_headers, test_db):
    """Regression: document signals still list missing documents."""
    test_client = seed_client_identity(
        test_db,
        full_name="S5 Notification Client",
        id_number="555555552",
    )
    test_db.commit()

    response = client.get(
        f"/api/v1/documents/client/{test_client.id}/signals",
        headers=secretary_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "missing_documents" in data
