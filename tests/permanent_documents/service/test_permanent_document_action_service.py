from datetime import date

import pytest

from app.clients.models import Client, ClientType
from app.core.exceptions import NotFoundError
from app.permanent_documents.models.permanent_document import DocumentStatus, DocumentType, PermanentDocument
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
from app.permanent_documents.services.permanent_document_action_service import PermanentDocumentActionService


def _client(db) -> Client:
    crm_client = Client(
        full_name="Perm Action Client",
        id_number="PDAS001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def _doc(db, client_id: int, annual_report_id: int | None = None) -> PermanentDocument:
    return PermanentDocumentRepository(db).create(
        client_id=client_id,
        document_type=DocumentType.ID_COPY,
        storage_key="clients/x/id_copy/a.pdf",
        uploaded_by=1,
        annual_report_id=annual_report_id,
    )


def test_approve_reject_update_notes_and_list_versions(test_db):
    crm_client = _client(test_db)
    doc = _doc(test_db, crm_client.id, annual_report_id=10)
    service = PermanentDocumentActionService(test_db)

    approved = service.approve_document(doc.id, approved_by=7)
    assert approved.status == DocumentStatus.APPROVED
    assert approved.approved_by == 7
    assert approved.approved_at is not None

    rejected = service.reject_document(doc.id, notes="bad")
    assert rejected.status == DocumentStatus.REJECTED
    assert rejected.notes == "bad"

    noted = service.update_notes(doc.id, notes="final note")
    assert noted.notes == "final note"

    versions = service.get_document_versions(crm_client.id, DocumentType.ID_COPY)
    assert len(versions) == 1
    by_report = service.list_by_annual_report(10)
    assert len(by_report) == 1


def test_action_service_not_found_or_deleted_raises(test_db):
    crm_client = _client(test_db)
    doc = _doc(test_db, crm_client.id)
    doc.is_deleted = True
    test_db.commit()

    service = PermanentDocumentActionService(test_db)

    with pytest.raises(NotFoundError):
        service.approve_document(doc.id, approved_by=1)

    with pytest.raises(NotFoundError):
        service.update_notes(999999, notes="x")
