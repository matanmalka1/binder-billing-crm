from datetime import date

from app.clients.models.client import Client, ClientType
from app.permanent_documents.models.permanent_document import DocumentType
from app.permanent_documents.repositories.permanent_document_repository import (
    PermanentDocumentRepository,
)
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(
        full_name="Permanent Doc Admin",
        email="permdoc.admin@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db, *, name: str, id_number: str) -> Client:
    client = Client(
        full_name=name,
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_count_by_client_ignores_soft_deleted_documents(test_db):
    user = _user(test_db)
    repo = PermanentDocumentRepository(test_db)
    client_a = _client(test_db, name="Permanent A", id_number="PD001")
    client_b = _client(test_db, name="Permanent B", id_number="PD002")

    active = repo.create(
        client_id=client_a.id,
        document_type=DocumentType.ID_COPY,
        storage_key="clients/1/id_copy/a.pdf",
        uploaded_by=user.id,
    )
    deleted = repo.create(
        client_id=client_a.id,
        document_type=DocumentType.POWER_OF_ATTORNEY,
        storage_key="clients/1/power_of_attorney/b.pdf",
        uploaded_by=user.id,
    )
    repo.create(
        client_id=client_b.id,
        document_type=DocumentType.ENGAGEMENT_AGREEMENT,
        storage_key="clients/2/engagement_agreement/c.pdf",
        uploaded_by=user.id,
    )

    deleted.is_deleted = True
    test_db.commit()

    assert active.is_deleted is False
    assert repo.count_by_client(client_a.id) == 1
    assert repo.count_by_client(client_b.id) == 1

