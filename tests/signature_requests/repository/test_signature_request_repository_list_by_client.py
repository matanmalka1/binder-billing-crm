from datetime import date

from app.clients.models import Client, ClientType
from app.signature_requests.models.signature_request import SignatureRequestStatus, SignatureRequestType
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(
        full_name="Sig Repo List User",
        email="sig.repo.list@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db, suffix: str) -> Client:
    client = Client(
        full_name=f"Sig Repo List Client {suffix}",
        id_number=f"SIG-LIST-{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_signature_request_repository_list_by_client_with_status(test_db):
    repo = SignatureRequestRepository(test_db)
    user = _user(test_db)
    client = _client(test_db, "A")

    draft = repo.create(
        client_id=client.id,
        created_by=user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Draft",
        signer_name="Signer",
    )
    pending = repo.create(
        client_id=client.id,
        created_by=user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Pending",
        signer_name="Signer",
    )
    repo.update(pending.id, status=SignatureRequestStatus.PENDING_SIGNATURE)

    all_items = repo.list_by_client(client.id, page=1, page_size=10)
    assert {r.id for r in all_items} == {draft.id, pending.id}

    pending_only = repo.list_by_client(
        client.id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        page=1,
        page_size=10,
    )
    assert [r.id for r in pending_only] == [pending.id]
