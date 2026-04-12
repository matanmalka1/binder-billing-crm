from datetime import date

import pytest

from app.businesses.models.business import Business, EntityType
from app.clients.models.client import Client, IdNumberType
from app.core.exceptions import NotFoundError
from app.permanent_documents.models.permanent_document import (
    DocumentScope,
    DocumentStatus,
    DocumentType,
    PermanentDocument,
)
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
from app.permanent_documents.services.permanent_document_action_service import PermanentDocumentActionService


def _business(db) -> Business:
    client = Client(
        full_name="Perm Action Client",
        id_number="71040001",
        id_number_type=IdNumberType.CORPORATION,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name="Perm Action Biz",
        entity_type=EntityType.COMPANY_LTD,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _doc(db, business: Business, annual_report_id: int | None = None) -> PermanentDocument:
    return PermanentDocumentRepository(db).create(
        client_id=business.client_id,
        business_id=business.id,
        scope=DocumentScope.CLIENT,
        document_type=DocumentType.ID_COPY,
        storage_key="businesses/x/id_copy/a.pdf",
        uploaded_by=1,
        annual_report_id=annual_report_id,
    )


def test_approve_reject_update_notes_and_list_versions(test_db):
    business = _business(test_db)
    doc = _doc(test_db, business, annual_report_id=10)
    service = PermanentDocumentActionService(test_db)

    approved = service.approve_document(doc.id, approved_by=7)
    assert approved.status == DocumentStatus.APPROVED
    assert approved.approved_by == 7
    assert approved.approved_at is not None

    rejected = service.reject_document(doc.id, notes="bad", rejected_by=8)
    assert rejected.status == DocumentStatus.REJECTED
    assert rejected.notes == "bad"
    assert rejected.rejected_by == 8
    assert rejected.rejected_at is not None

    noted = service.update_notes(doc.id, notes="final note")
    assert noted.notes == "final note"

    versions = service.get_document_versions(business.client_id, DocumentType.ID_COPY)
    assert len(versions) == 1
    by_report = service.list_by_annual_report(10)
    assert len(by_report) == 1


def test_action_service_not_found_or_deleted_raises(test_db):
    business = _business(test_db)
    doc = _doc(test_db, business)
    doc.is_deleted = True
    test_db.commit()

    service = PermanentDocumentActionService(test_db)

    with pytest.raises(NotFoundError):
        service.approve_document(doc.id, approved_by=1)

    with pytest.raises(NotFoundError):
        service.update_notes(999999, notes="x")
