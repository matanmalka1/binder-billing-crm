from tests.vat_reports.api.test_vat_reports_utils import setup_ready_item


class TestFiling:
    def test_file_vat_return(self, client, advisor_headers, vat_client):
        item_id = setup_ready_item(client, advisor_headers, vat_client, "2026-12")
        response = client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={"filing_method": "online"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "filed"
        assert data["filing_method"] == "online"
        assert data["is_overridden"] is False

    def test_cannot_file_without_advisor_role(self, client, secretary_headers, vat_client):
        response = client.post(
            "/api/v1/vat/work-items/1/file",
            headers=secretary_headers,
            json={"filing_method": "online"},
        )
        assert response.status_code == 403

    def test_cannot_add_invoice_after_filing(self, client, advisor_headers, vat_client):
        item_id = setup_ready_item(client, advisor_headers, vat_client, "2025-01")
        client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={"filing_method": "manual"},
        )
        response = client.post(
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
        assert response.status_code == 400

    def test_override_with_justification_works(self, client, advisor_headers, vat_client):
        item_id = setup_ready_item(client, advisor_headers, vat_client, "2025-02")
        response = client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={
                "filing_method": "manual",
                "override_amount": "200.00",
                "override_justification": "Corrected invoice received post-review",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_overridden"] is True
        assert data["final_vat_amount"] == "200.00"

    def test_override_without_justification_400(self, client, advisor_headers, vat_client):
        item_id = setup_ready_item(client, advisor_headers, vat_client, "2025-03")
        response = client.post(
            f"/api/v1/vat/work-items/{item_id}/file",
            headers=advisor_headers,
            json={"filing_method": "online", "override_amount": "999.00"},
        )
        assert response.status_code == 400
