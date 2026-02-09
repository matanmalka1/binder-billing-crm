from datetime import date
from io import BytesIO

from app.models import Client, ClientType, DocumentType
from app.services import PermanentDocumentService


def test_upload_permanent_document(test_db, test_user):
    """Test uploading a permanent document."""
    client = Client(
        full_name="Doc Test Client",
        id_number="666666666",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    service = PermanentDocumentService(test_db)
    file_data = BytesIO(b"fake document content")

    document = service.upload_document(
        client_id=client.id,
        document_type=DocumentType.ID_COPY,
        file_data=file_data,
        filename="id_copy.pdf",
        uploaded_by=test_user.id,
    )

    assert document is not None
    assert document.client_id == client.id
    assert document.document_type == DocumentType.ID_COPY
    assert document.is_present is True
    assert document.uploaded_by == test_user.id


def test_missing_document_types(test_db):
    """Test getting missing document types for a client."""
    client = Client(
        full_name="Missing Doc Client",
        id_number="777777777",
        client_type=ClientType.OSEK_PATUR,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    service = PermanentDocumentService(test_db)

    # Initially, all document types are missing
    missing = service.get_missing_document_types(client.id)
    assert len(missing) == 3
    assert DocumentType.ID_COPY in missing
    assert DocumentType.POWER_OF_ATTORNEY in missing
    assert DocumentType.ENGAGEMENT_AGREEMENT in missing

    # Upload one document
    file_data = BytesIO(b"fake content")
    service.upload_document(
        client_id=client.id,
        document_type=DocumentType.ID_COPY,
        file_data=file_data,
        filename="id.pdf",
        uploaded_by=1,
    )

    # Now only 2 should be missing
    missing_after = service.get_missing_document_types(client.id)
    assert len(missing_after) == 2
    assert DocumentType.ID_COPY not in missing_after


def test_upload_document_client_not_found(test_db):
    """Test that uploading document for non-existent client raises error."""
    service = PermanentDocumentService(test_db)
    file_data = BytesIO(b"fake content")

    try:
        service.upload_document(
            client_id=99999,
            document_type=DocumentType.ID_COPY,
            file_data=file_data,
            filename="test.pdf",
            uploaded_by=1,
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e).lower()