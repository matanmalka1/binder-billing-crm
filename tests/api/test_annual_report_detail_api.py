from datetime import date, datetime

from app.clients.models import Client, ClientType
from app.annual_reports.services import AnnualReportService


def _create_report(test_db):
    client = Client(
        full_name="Annual Report Client",
        id_number="333333333",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    service = AnnualReportService(test_db)
    report = service.create_report(
        client_id=client.id,
        tax_year=2025,
        due_date=date(2026, 4, 30),
    )
    return report


def test_get_detail_returns_blank_when_missing(client, test_db, advisor_headers):
    report = _create_report(test_db)

    response = client.get(
        f"/api/v1/annual-reports/{report.id}/details",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["report_id"] == report.id
    assert data["tax_refund_amount"] is None
    assert data["tax_due_amount"] is None
    assert data["client_approved_at"] is None
    assert data["internal_notes"] is None


def test_update_detail_creates_and_updates(client, test_db, advisor_headers):
    report = _create_report(test_db)

    first_response = client.patch(
        f"/api/v1/annual-reports/{report.id}/details",
        headers=advisor_headers,
        json={
            "tax_refund_amount": 1200.5,
            "tax_due_amount": 300.0,
            "client_approved_at": "2026-02-15T12:00:00",
            "internal_notes": "Initial review complete",
        },
    )

    assert first_response.status_code == 200
    first = first_response.json()
    assert first["tax_refund_amount"] == 1200.5
    assert first["tax_due_amount"] == 300.0
    assert first["client_approved_at"] == "2026-02-15T12:00:00"
    assert first["internal_notes"] == "Initial review complete"
    assert first["updated_at"] is None

    # Second patch should set updated_at
    follow_up = client.patch(
        f"/api/v1/annual-reports/{report.id}/details",
        headers=advisor_headers,
        json={"tax_due_amount": 450.25, "internal_notes": "Adjusted figures"},
    )

    assert follow_up.status_code == 200
    data = follow_up.json()
    assert data["tax_due_amount"] == 450.25
    assert data["internal_notes"] == "Adjusted figures"
    assert data["updated_at"] is not None


def test_annual_report_detail_missing_report_returns_404(client, advisor_headers):
    response = client.get(
        "/api/v1/annual-reports/999/details",
        headers=advisor_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Annual report not found"

    patch_response = client.patch(
        "/api/v1/annual-reports/999/details",
        headers=advisor_headers,
        json={"tax_due_amount": 10},
    )
    assert patch_response.status_code == 404
    assert patch_response.json()["detail"] == "Annual report not found"
