from datetime import date

from app.businesses.models.business import Business
from app.common.enums import EntityType
from app.clients.models.client import Client, IdNumberType
from app.permanent_documents.models.permanent_document import DocumentScope, DocumentType
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository


def _business(db) -> Business:
    client = Client(
        full_name="Perm Action API Client",
        id_number="71070001",
        id_number_type=IdNumberType.CORPORATION,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name="Perm Action API Biz",
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _doc(db, business: Business, annual_report_id: int | None = None):
    return PermanentDocumentRepository(db).create(
        client_id=business.client_id,
        business_id=business.id,
        scope=DocumentScope.CLIENT,
        document_type=DocumentType.ID_COPY,
        storage_key="businesses/x/id_copy/api.pdf",
        uploaded_by=1,
        annual_report_id=annual_report_id,
    )


def test_actions_endpoints_approve_reject_notes_versions_and_list(client, test_db, advisor_headers):
    business = _business(test_db)
    doc = _doc(test_db, business, annual_report_id=55)

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
        f"/api/v1/documents/client/{business.client_id}/versions?document_type=id_copy",
        headers=advisor_headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()["items"]) == 1

    by_report = client.get(f"/api/v1/documents/annual-report/55", headers=advisor_headers)
    assert by_report.status_code == 200
    assert len(by_report.json()["items"]) == 1
