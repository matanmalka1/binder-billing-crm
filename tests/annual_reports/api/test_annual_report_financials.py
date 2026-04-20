from itertools import count

from app.annual_reports.services.annual_report_service import AnnualReportService
from app.clients.models.client import Client


_client_seq = count(1)


def _create_report(db):
    client = Client(
        full_name="Financial Client",
        id_number=f"56565656{next(_client_seq)}",
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    svc = AnnualReportService(db)
    return svc.create_report(
        client_record_id=client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
        notes=None,
    )


def test_create_income_line_accepts_zero_amount(client, test_db, advisor_headers):
    report = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report.id}/income",
        headers=advisor_headers,
        json={"source_type": "salary", "amount": 0, "description": "Zeroed correction"},
    )

    assert resp.status_code == 201
    assert resp.json()["amount"] == "0.00"


def test_create_expense_line_accepts_legacy_document_ref_alias_and_returns_new_field(
    client, test_db, advisor_headers
):
    report = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report.id}/expenses",
        headers=advisor_headers,
        json={
            "category": "office_rent",
            "amount": 250,
            "supporting_document_ref": "INV-EXT-001",
        },
    )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["external_document_reference"] == "INV-EXT-001"
    assert "supporting_document_ref" not in payload
