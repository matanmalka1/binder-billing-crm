import pytest

from tests.vat_reports.api.test_vat_reports_utils import create_work_item


class TestCreateWorkItem:
    def test_create_work_item_201(self, client, advisor_headers, vat_client):
        item_id = create_work_item(client, advisor_headers, vat_client, "2026-01")
        assert isinstance(item_id, int)

    def test_duplicate_period_400(self, client, advisor_headers, vat_client):
        payload = {"business_id": vat_client.id, "period": "2026-02"}
        client.post("/api/v1/vat/work-items", headers=advisor_headers, json=payload)
        response = client.post("/api/v1/vat/work-items", headers=advisor_headers, json=payload)
        assert response.status_code == 409
        assert response.json()["error"] == "VAT.CONFLICT"

    def test_invalid_period_format_422(self, client, advisor_headers, vat_client):
        response = client.post(
            "/api/v1/vat/work-items",
            headers=advisor_headers,
            json={"business_id": vat_client.id, "period": "01-2026"},
        )
        assert response.status_code == 422

    def test_pending_materials_requires_note_400(self, client, advisor_headers, vat_client):
        response = client.post(
            "/api/v1/vat/work-items",
            headers=advisor_headers,
            json={"business_id": vat_client.id, "period": "2026-03", "mark_pending": True},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "VAT.PENDING_NOTE_REQUIRED"

    def test_unauthenticated_401(self, client, vat_client):
        response = client.post(
            "/api/v1/vat/work-items",
            json={"business_id": vat_client.id, "period": "2026-04"},
        )
        assert response.status_code == 401
