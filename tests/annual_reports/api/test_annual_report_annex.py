from datetime import date
from itertools import count

import pytest

from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.annual_reports.repositories.annex_data_repository import AnnexDataRepository
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.clients.models.client import Client


_client_seq = count(1)


def _create_report(db):
    client = Client(
        full_name="Annex Client",
        id_number=f"45454545{next(_client_seq)}",

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


def test_annex_crud_flow(client, test_db, advisor_headers):
    report = _create_report(test_db)
    schedule = "schedule_b"

    create = client.post(
        f"/api/v1/annual-reports/{report.id}/annex/{schedule}",
        headers=advisor_headers,
        json={"data": {"rental_income": 12000}, "notes": "First line"},
    )
    assert create.status_code == 201
    line_id = create.json()["id"]
    assert create.json()["line_number"] == 1

    update = client.patch(
        f"/api/v1/annual-reports/{report.id}/annex/{schedule}/{line_id}",
        headers=advisor_headers,
        json={"data": {"rental_income": 15000}, "notes": "Updated"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["rental_income"] == 15000

    listing = client.get(
        f"/api/v1/annual-reports/{report.id}/annex/{schedule}",
        headers=advisor_headers,
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    delete = client.delete(
        f"/api/v1/annual-reports/{report.id}/annex/{schedule}/{line_id}",
        headers=advisor_headers,
    )
    assert delete.status_code == 204
    assert client.get(
        f"/api/v1/annual-reports/{report.id}/annex/{schedule}",
        headers=advisor_headers,
    ).json() == []


def test_add_annex_requires_report_exists(client, advisor_headers):
    resp = client.post(
        "/api/v1/annual-reports/999/annex/schedule_b",
        headers=advisor_headers,
        json={"data": {"rental_income": 1000}},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "ANNUAL_REPORT.NOT_FOUND"
