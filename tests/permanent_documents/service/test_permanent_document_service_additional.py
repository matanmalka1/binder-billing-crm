from datetime import date
from io import BytesIO

import pytest

from app.clients.models.client import Client, ClientType
from app.core.exceptions import AppError, NotFoundError
from app.permanent_documents.models.permanent_document import DocumentType
from app.permanent_documents.services.permanent_document_service import PermanentDocumentService


class _Storage:
    def __init__(self):
        self.uploads = []

    def upload(self, key, file_data, content_type):
        self.uploads.append((key, content_type))
        return key

    def delete(self, key):
        return None

    def get_presigned_url(self, key, expires_in=3600):
        return f"/dl/{key}?exp={expires_in}"


def _client(test_db):
    c = Client(
        full_name="PermDoc Extra",
        id_number="PDE001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def test_permanent_document_size_mime_and_download_not_found(test_db, test_user):
    c = _client(test_db)
    service = PermanentDocumentService(test_db, storage=_Storage())

    with pytest.raises(AppError) as size_exc:
        service.upload_document(
            client_id=c.id,
            document_type=DocumentType.ID_COPY,
            file_data=BytesIO(b"x" * (11 * 1024 * 1024)),
            filename="big.pdf",
            uploaded_by=test_user.id,
            mime_type="application/pdf",
        )
    assert size_exc.value.code == "DOCUMENT.FILE_TOO_LARGE"
    assert size_exc.value.status_code == 422

    with pytest.raises(AppError) as mime_exc:
        service.upload_document(
            client_id=c.id,
            document_type=DocumentType.ID_COPY,
            file_data=BytesIO(b"ok"),
            filename="bad.bin",
            uploaded_by=test_user.id,
            mime_type="application/octet-stream",
        )
    assert mime_exc.value.code == "DOCUMENT.INVALID_FILE_TYPE"
    assert mime_exc.value.status_code == 422

    with pytest.raises(NotFoundError):
        service.get_download_url(999999)


def test_permanent_document_replace_and_version_increment(test_db, test_user):
    c = _client(test_db)
    storage = _Storage()
    service = PermanentDocumentService(test_db, storage=storage)
    doc = service.upload_document(
        client_id=c.id,
        document_type=DocumentType.ID_COPY,
        file_data=BytesIO(b"first"),
        filename="id.pdf",
        uploaded_by=test_user.id,
        mime_type="application/pdf",
    )
    replaced = service.replace_document(
        document_id=doc.id,
        file_data=BytesIO(b"second"),
        filename="id2.pdf",
        uploaded_by=test_user.id,
    )
    assert replaced.version == 2
    assert "v2_" in replaced.storage_key

    url = service.get_download_url(replaced.id, expires_in=120)
    assert "exp=120" in url
