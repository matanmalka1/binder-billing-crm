from datetime import date

from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.signature_requests.models.signature_request import SignatureRequestStatus, SignatureRequestType
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(full_name="Sig Repo List User", email="sig.repo.list@example.com", password_hash=AuthService.hash_password("pass"), role=UserRole.ADVISOR, is_active=True)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _business(test_db, suffix: str) -> Business:
    client = Client(full_name=f"Sig Repo List Client {suffix}", id_number=f"SIG-LIST-{suffix}")
    test_db.add(client)
    test_db.flush()
    business = Business(client_id=client.id, business_name=f"Sig Repo List Business {suffix}", opened_at=date(2026, 1, 1))
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_signature_request_repository_list_by_business_with_status(test_db):
    repo = SignatureRequestRepository(test_db)
    user = _user(test_db)
    business = _business(test_db, "A")
    draft = repo.create(client_id=business.client_id, client_record_id=business.client_id, business_id=business.id, created_by=user.id, request_type=SignatureRequestType.CUSTOM, title="Draft", signer_name="Signer")
    pending = repo.create(client_id=business.client_id, client_record_id=business.client_id, business_id=business.id, created_by=user.id, request_type=SignatureRequestType.CUSTOM, title="Pending", signer_name="Signer")
    repo.update(pending.id, status=SignatureRequestStatus.PENDING_SIGNATURE)
    assert {r.id for r in repo.list_by_business(business.id, page=1, page_size=10)} == {draft.id, pending.id}
    pending_only = repo.list_by_business(business.id, status=SignatureRequestStatus.PENDING_SIGNATURE, page=1, page_size=10)
    assert [r.id for r in pending_only] == [pending.id]
