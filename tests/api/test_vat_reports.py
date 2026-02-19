"""
Integration tests for VAT Reports API endpoints.

Uses the same test fixtures and pattern as the rest of the test suite.
"""

from datetime import date

import pytest

from app.clients.models.client import Client, ClientType


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def vat_client(test_db):
    """A client to attach VAT work items to."""
    c = Client(
        full_name="VAT Test Client",
        id_number="VAT999001",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


# ─── Work item creation ───────────────────────────────────────────────────────

class TestCreateWorkItem:
    def test_create_work_item_201(self, client, advisor_headers, vat_client):
        response = client.post(
            "/api/v1/vat/work-items",
            headers=advisor_headers,
            json={"client_id": vat_client.id, "period": "2026-01"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == vat_client.id
        assert data["period"] == "2026-01"
        assert data["status"] == "material_received"

    def test_duplicate_period_400(self, client, advisor_headers, vat_client):
        payload = {"client_id": vat_client.id, "period": "2026-02"}
        client.post("/api/v1/vat/work-items", headers=advisor_headers, json=payload)
        response = client.post("/api/v1/vat/work-items", headers=advisor_headers, json=payload)
        assert response.status_code == 400

    def test_invalid_period_format_422(self, client, advisor_headers, vat_client):
        response = client.post(
            "/api/v1/vat/work-items",
            headers=advisor_headers,
            json={"client_id": vat_client.id, "period": "01-2026"},
        )
        assert response.status_code == 422

    def test_pending_materials_requires_note_400(self, client, advisor_headers, vat_client):
        response = client.post(
            "/api/v1/vat/work-items",
            headers=advisor_headers,
            json={
                "client_id": vat_client.id,
                "period": "2026-03",
                "mark_pending": True,
            },
        )
        assert response.status_code == 400

    def test_unauthenticated_401(self, client, vat_client):
        response = client.post(
            "/api/v1/vat/work-items",
            json={"client_id": vat_client.id, "period": "2026-04"},
        )
        assert response.status_code == 401


# ─── Invoice add / list / delete ─────────────────────────────────────────────

class TestInvoices:
    def _create_item(self, client, headers, vat_client, period="2026-05"):
        r = client.post(
            "/api/v1/vat/work-items",
            headers=headers,
            json={"client_id": vat_client.id, "period": period},
        )
        assert r.status_code == 201
        return r.json()["id"]

    def _income_payload(self, invoice_number="INV-001"):
        return {
            "invoice_type": "income",
            "invoice_number": invoice_number,
            "invoice_date": "2026-01-15T00:00:00",
            "counterparty_name": "Customer A",
            "net_amount": "1000.00",
            "vat_amount": "170.00",
        }

    def test_add_income_invoice_201(self, client, advisor_headers, vat_client):
        item_id = self._create_item(client, advisor_headers, vat_client)
        response = client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json=self._income_payload(),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["invoice_type"] == "income"
        assert data["vat_amount"] == "170.00"

    def test_add_invoice_updates_totals(self, client, advisor_headers, vat_client):
        item_id = self._create_item(client, advisor_headers, vat_client, period="2026-06")
        client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json=self._income_payload("INV-001"),
        )
        r = client.get(f"/api/v1/vat/work-items/{item_id}", headers=advisor_headers)
        data = r.json()
        assert float(data["total_output_vat"]) == 170.0
        assert data["status"] == "data_entry_in_progress"

    def test_negative_vat_rejected_400(self, client, advisor_headers, vat_client):
        item_id = self._create_item(client, advisor_headers, vat_client, period="2026-07")
        payload = self._income_payload()
        payload["vat_amount"] = "-10.00"
        response = client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json=payload,
        )
        assert response.status_code in (400, 422)

    def test_expense_without_category_400(self, client, advisor_headers, vat_client):
        item_id = self._create_item(client, advisor_headers, vat_client, period="2026-08")
        payload = {
            "invoice_type": "expense",
            "invoice_number": "EXP-001",
            "invoice_date": "2026-01-15T00:00:00",
            "counterparty_name": "Supplier",
            "net_amount": "500.00",
            "vat_amount": "85.00",
        }
        response = client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json=payload,
        )
        assert response.status_code == 400

    def test_list_invoices(self, client, advisor_headers, vat_client):
        item_id = self._create_item(client, advisor_headers, vat_client, period="2026-09")
        client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json=self._income_payload("INV-001"),
        )
        client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json=self._income_payload("INV-002"),
        )
        r = client.get(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) == 2

    def test_delete_invoice(self, client, advisor_headers, vat_client):
        item_id = self._create_item(client, advisor_headers, vat_client, period="2026-10")
        inv_r = client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json=self._income_payload(),
        )
        invoice_id = inv_r.json()["id"]

        del_r = client.delete(
            f"/api/v1/vat/work-items/{item_id}/invoices/{invoice_id}",
            headers=advisor_headers,
        )
        assert del_r.status_code == 204


# ─── Status transitions ───────────────────────────────────────────────────────

class TestStatusTransitions:
    def _setup_item_with_invoice(self, client, headers, vat_client, period):
        r = client.post(
            "/api/v1/vat/work-items",
            headers=headers,
            json={"client_id": vat_client.id, "period": period},
        )
        item_id = r.json()["id"]
        client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=headers,
            json={
                "invoice_type": "income",
                "invoice_number": "INV-001",
                "invoice_date": "2026-01-15T00:00:00",
                "counterparty_name": "Customer",
                "net_amount": "1000.00",
                "vat_amount": "170.00",
            },
        )
        return item_id

    def test_mark_ready_for_review(self, client, advisor_headers, vat_client):
        item_id = self._setup_item_with_invoice(
            client, advisor_headers, vat_client, "2026-11"
        )
        r = client.post(
            f"/api/v1/vat/work-items/{item_id}/ready-for-review",
            headers=advisor_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ready_for_review"

    def test_send_back_requires_advisor(self, client, secretary_headers, vat_client):
        # Secretary should be forbidden from send-back
        r = client.post(
            "/api/v1/vat/work-items/1/send-back",
            headers=secretary_headers,
            json={"correction_note": "Please fix invoice 2"},
        )
        assert r.status_code == 403


# ─── Filing ───────────────────────────────────────────────────────────────────

class TestFiling:
    def _setup_ready_item(self, client, headers, vat_client, period):
        r = client.post(
            "/api/v1/vat/work-items",
            headers=headers,
            json={"client_id": vat_client.id, "period": period},
        )
        item_id = r.json()["id"]
        client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=headers,
            json={
                "invoice_type": "income",
                "invoice_number": "INV-001",
                "invoice_date": "2026-01-15T00:00:00",
                "counterparty_name": "Customer",
                "net_amount": "1000.00",
                "vat_amount": "170.00",
            },
        )
        client.post(
            f"/api/v1/vat/work-items/{item_id}/ready-for-review",
            headers=headers,
        )
        return item_id

    def test_file_vat_return(self, client, advisor_headers, vat_client):
        item_id = self._setup_ready_item(client, advisor_headers, vat_client, "2026-12")
        r = client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={"filing_method": "online"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "filed"
        assert data["filing_method"] == "online"
        assert data["is_overridden"] is False

    def test_cannot_file_without_advisor_role(self, client, secretary_headers, vat_client):
        r = client.post(
            "/api/v1/vat/work-items/1/file",
            headers=secretary_headers,
            json={"filing_method": "online"},
        )
        assert r.status_code == 403

    def test_cannot_add_invoice_after_filing(self, client, advisor_headers, vat_client):
        item_id = self._setup_ready_item(client, advisor_headers, vat_client, "2025-01")
        client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={"filing_method": "manual"},
        )
        r = client.post(
            f"/api/v1/vat/work-items/{item_id}/invoices",
            headers=advisor_headers,
            json={
                "invoice_type": "income",
                "invoice_number": "INV-999",
                "invoice_date": "2026-01-20T00:00:00",
                "counterparty_name": "Late customer",
                "net_amount": "500.00",
                "vat_amount": "85.00",
            },
        )
        assert r.status_code == 400

    def test_override_with_justification_works(self, client, advisor_headers, vat_client):
        item_id = self._setup_ready_item(client, advisor_headers, vat_client, "2025-02")
        r = client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={
                "filing_method": "manual",
                "override_amount": "200.00",
                "override_justification": "Corrected invoice received post-review",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["is_overridden"] is True
        assert data["final_vat_amount"] == "200.00"

    def test_override_without_justification_400(self, client, advisor_headers, vat_client):
        item_id = self._setup_ready_item(client, advisor_headers, vat_client, "2025-03")
        r = client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={"filing_method": "online", "override_amount": "999.00"},
        )
        assert r.status_code == 400


# ─── Audit trail ──────────────────────────────────────────────────────────────

class TestAuditTrail:
    def test_audit_trail_populated(self, client, advisor_headers, vat_client):
        r = client.post(
            "/api/v1/vat/work-items",
            headers=advisor_headers,
            json={"client_id": vat_client.id, "period": "2025-04"},
        )
        item_id = r.json()["id"]

        r = client.get(
            f"/api/v1/vat/work-items/{item_id}/audit",
            headers=advisor_headers,
        )
        assert r.status_code == 200
        entries = r.json()["items"]
        assert len(entries) >= 1
        assert entries[0]["action"] == "material_received"
