from datetime import date

import pytest

from app.clients.models.client import Client, ClientType
from app.core.exceptions import NotFoundError
from app.permanent_documents.models.permanent_document import DocumentType
from app.permanent_documents.repositories.permanent_document_repository import (
    PermanentDocumentRepository,
)
from app.permanent_documents.services.permanent_document_service import (
    PermanentDocumentService,
)
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(
        full_name="Permanent Service User",
        email="permanent.service@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db) -> Client:
    client = Client(
        full_name="Permanent Service Client",
        id_number="PSD001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_list_client_documents_and_delete_document(test_db):
    user = _user(test_db)
    client = _client(test_db)
    repo = PermanentDocumentRepository(test_db)
    service = PermanentDocumentService(test_db)

    doc_2025 = repo.create(
        client_id=client.id,
        document_type=DocumentType.ID_COPY,
        storage_key="clients/1/id_copy/2025.pdf",
        uploaded_by=user.id,
        tax_year=2025,
    )
    doc_2024 = repo.create(
        client_id=client.id,
        document_type=DocumentType.POWER_OF_ATTORNEY,
        storage_key="clients/1/power_of_attorney/2024.pdf",
        uploaded_by=user.id,
        tax_year=2024,
    )

    all_docs = service.list_client_documents(client.id)
    assert {d.id for d in all_docs} == {doc_2025.id, doc_2024.id}

    docs_2025 = service.list_client_documents(client.id, tax_year=2025)
    assert [d.id for d in docs_2025] == [doc_2025.id]

    service.delete_document(doc_2024.id)
    remaining = service.list_client_documents(client.id)
    assert [d.id for d in remaining] == [doc_2025.id]

    with pytest.raises(NotFoundError) as exc_info:
        service.delete_document(doc_2024.id)
    assert exc_info.value.code == "PERMANENT_DOCUMENTS.NOT_FOUND"

