from datetime import date
from io import BytesIO

import pytest

from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client, IdNumberType
from app.core.exceptions import NotFoundError
from app.permanent_documents.models.permanent_document import DocumentType
from app.permanent_documents.services.permanent_document_service import (
    PermanentDocumentService,
)


def _business(test_db, *, suffix: str) -> Business:
    client = Client(
        full_name=f"Doc Test Client {suffix}",
        id_number=f"7101000{suffix}",
        id_number_type=IdNumberType.CORPORATION,
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Doc Test Biz {suffix}",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_upload_permanent_document(test_db, test_user):
    """Test uploading a permanent document."""
    business = _business(test_db, suffix="1")

    service = PermanentDocumentService(test_db)
    file_data = BytesIO(b"fake document content")

    document = service.upload_document(
        business_id=business.id,
        document_type=DocumentType.ID_COPY,
        file_data=file_data,
        filename="id_copy.pdf",
        uploaded_by=test_user.id,
    )

    assert document is not None
    assert document.client_id == business.client_id
    assert document.business_id == business.id
    assert document.document_type == DocumentType.ID_COPY
    assert document.is_present is True
    assert document.uploaded_by == test_user.id


def test_missing_document_types(test_db, test_user):
    """Test getting missing document types for a business."""
    business = _business(test_db, suffix="2")
    service = PermanentDocumentService(test_db)

    # Initially, all default required types are missing
    missing = service.get_missing_document_types(business.id)
    assert len(missing) == 3
    assert DocumentType.ID_COPY.value in missing
    assert DocumentType.POWER_OF_ATTORNEY.value in missing
    assert DocumentType.ENGAGEMENT_AGREEMENT.value in missing

    # Upload one required document
    file_data = BytesIO(b"fake content")
    service.upload_document(
        business_id=business.id,
        document_type=DocumentType.ID_COPY,
        file_data=file_data,
        filename="id.pdf",
        uploaded_by=test_user.id,
    )

    # Now only 2 should be missing
    missing_after = service.get_missing_document_types(business.id)
    assert len(missing_after) == 2
    assert DocumentType.ID_COPY.value not in missing_after


def test_upload_document_business_not_found(test_db):
    """Test that uploading document for non-existent business raises error."""
    service = PermanentDocumentService(test_db)
    file_data = BytesIO(b"fake content")

    with pytest.raises(NotFoundError) as exc_info:
        service.upload_document(
            business_id=99999,
            document_type=DocumentType.ID_COPY,
            file_data=file_data,
            filename="test.pdf",
            uploaded_by=1,
        )
    assert exc_info.value.code == "PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND"
