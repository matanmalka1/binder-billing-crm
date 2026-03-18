from datetime import date

from app.clients.models import Client, ClientType
from app.permanent_documents.models.permanent_document import DocumentType
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository


def _client(db) -> Client:
    crm_client = Client(
        full_name="Perm Action API Client",
        id_number="PDAAPI001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def _doc(db, client_id: int, annual_report_id: int | None = None):
    return PermanentDocumentRepository(db).create(
        client_id=client_id,
        document_type=DocumentType.ID_COPY,
        storage_key="clients/x/id_copy/api.pdf",
        uploaded_by=1,
        annual_report_id=annual_report_id,
    )


def test_actions_endpoints_approve_reject_notes_versions_and_list(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    doc = _doc(test_db, crm_client.id, annual_report_id=55)

    approve = client.post(f"/api/v1/documents/{doc.id}/approve", headers=advisor_headers, json={})
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    reject = client.post(
        f"/api/v1/documents/{doc.id}/reject",
        headers=advisor_headers,
        json={"notes": "missing signature"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    notes = client.patch(
        f"/api/v1/documents/{doc.id}/notes",
        headers=advisor_headers,
        json={"notes": "fixed"},
    )
    assert notes.status_code == 200
    assert notes.json()["notes"] == "fixed"

    versions = client.get(
        f"/api/v1/documents/client/{crm_client.id}/versions?document_type=id_copy",
        headers=advisor_headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()["items"]) == 1

    by_report = client.get(f"/api/v1/documents/annual-report/55", headers=advisor_headers)
    assert by_report.status_code == 200
    assert len(by_report.json()["items"]) == 1
