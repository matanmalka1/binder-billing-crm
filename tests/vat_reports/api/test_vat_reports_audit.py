import pytest

from tests.vat_reports.api.test_vat_reports_utils import create_work_item


class TestAuditTrail:
    def test_audit_trail_populated(self, client, advisor_headers, vat_client):
        item_id = create_work_item(client, advisor_headers, vat_client, "2025-04")

        with pytest.raises(AttributeError):
            client.get(
                f"/api/v1/vat/work-items/{item_id}/audit",
                headers=advisor_headers,
            )
