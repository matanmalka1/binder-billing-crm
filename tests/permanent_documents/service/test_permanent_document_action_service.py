from datetime import date

import pytest

from app.businesses.models.business import Business
from app.common.enums import IdNumberType
from app.core.exceptions import NotFoundError
from app.permanent_documents.models.permanent_document import (
    DocumentScope,
    DocumentType,
    PermanentDocument,
)
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
from app.permanent_documents.services.permanent_document_action_service import PermanentDocumentActionService
from tests.helpers.identity import seed_client_with_business


def _business(db) -> Business:
    _client, business = seed_client_with_business(
        db,
        full_name="Perm Action Client",
        id_number="71040001",
        id_number_type=IdNumberType.CORPORATION,
    )
    db.commit()
    return business


def _doc(db, business: Business, annual_report_id: int | None = None) -> PermanentDocument:
    return PermanentDocumentRepository(db).create(
        client_record_id=business.client_id,
        business_id=business.id,
        scope=DocumentScope.CLIENT,
        document_type=DocumentType.ID_COPY,
        storage_key="businesses/x/id_copy/a.pdf",
        uploaded_by=1,
        annual_report_id=annual_report_id,
    )


def test_update_notes_and_list_versions(test_db):
    business = _business(test_db)
    doc = _doc(test_db, business, annual_report_id=10)
    service = PermanentDocumentActionService(test_db)

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
        service.update_notes(999999, notes="x")
