from datetime import date
from itertools import count

from app.annual_reports.services.annual_report_service import AnnualReportService
from tests.helpers.identity import seed_client_identity


_client_seq = count(1)


def _client(db):
    idx = next(_client_seq)
    return seed_client_identity(db, full_name=f"Annual API Client {idx}", id_number=f"AAP{idx:03d}")


def test_client_and_tax_year_list_endpoints(client, test_db, advisor_headers, test_user):
    service = AnnualReportService(test_db)
    client_a = _client(test_db)
    client_b = _client(test_db)

    r1 = service.create_report(
        client_record_id=client_a.id,
        tax_year=2026,
        client_type="corporation",
        created_by=test_user.id,
        created_by_name="Test User",
    )
    r2 = service.create_report(
        client_record_id=client_a.id,
        tax_year=2025,
        client_type="corporation",
        created_by=test_user.id,
        created_by_name="Test User",
    )
    service.create_report(
        client_record_id=client_b.id,
        tax_year=2026,
        client_type="corporation",
        created_by=test_user.id,
        created_by_name="Test User",
    )

    client_reports = client.get(
        f"/api/v1/clients/{client_a.id}/annual-reports",
        headers=advisor_headers,
    )
    assert client_reports.status_code == 200
    assert [item["id"] for item in client_reports.json()["items"]] == [r1.id, r2.id]

    season_reports = client.get(
        "/api/v1/tax-year/2026/reports",
        headers=advisor_headers,
    )
    assert season_reports.status_code == 200
    data = season_reports.json()
    assert data["total"] == 2
    assert {item["tax_year"] for item in data["items"]} == {2026}
