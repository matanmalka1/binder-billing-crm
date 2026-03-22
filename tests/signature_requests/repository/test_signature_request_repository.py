from datetime import timedelta

from app.clients.models import Client
from app.signature_requests.models.signature_request import (
    SignatureAuditEvent,
    SignatureRequestStatus,
    SignatureRequest,
    SignatureRequestType,
)
from app.signature_requests.repositories.signature_request_repository import (
    SignatureRequestRepository,
)
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.utils.time_utils import utcnow


def _user(test_db) -> User:
    user = User(
        full_name="Signature Repo User",
        email="signature.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db, *, suffix: str) -> Client:
    client = Client(
        full_name=f"Signature Repo Client {suffix}",
        id_number=f"SIG-R-{suffix}",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_signature_request_repository_pending_expired_and_audit_methods(test_db):
    repo = SignatureRequestRepository(test_db)
    user = _user(test_db)
    client_a = _client(test_db, suffix="A")
    client_b = _client(test_db, suffix="B")
    now = utcnow()

    draft = repo.create(
        business_id=client_a.id,
        created_by=user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Draft",
        signer_name="Signer A",
    )
    expired_pending = repo.create(
        business_id=client_a.id,
        created_by=user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Expired Pending",
        signer_name="Signer B",
    )
    active_pending = repo.create(
        business_id=client_a.id,
        created_by=user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Active Pending",
        signer_name="Signer C",
    )
    other_client_pending = repo.create(
        business_id=client_b.id,
        created_by=user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Other Client",
        signer_name="Signer D",
    )

    repo.update(
        expired_pending.id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token="tok-expired",
        sent_at=now - timedelta(days=2),
        expires_at=now - timedelta(minutes=1),
    )
    repo.update(
        active_pending.id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token="tok-active",
        sent_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )
    repo.update(
        other_client_pending.id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token="tok-other",
        sent_at=now - timedelta(days=3),
        expires_at=now + timedelta(days=1),
    )

    assert repo.get_by_token("tok-active").id == active_pending.id
    assert repo.count_by_business(client_a.id) == 3
    assert repo.count_by_business(client_a.id, status=SignatureRequestStatus.PENDING_SIGNATURE) == 2

    pending = repo.list_pending(page=1, page_size=10)
    assert [item.id for item in pending] == [
        other_client_pending.id,
        expired_pending.id,
        active_pending.id,
    ]
    assert repo.count_pending() == 3

    expired = repo.list_expired_pending()
    assert [item.id for item in expired] == [expired_pending.id]
    assert draft.id not in [item.id for item in expired]

    late = repo.append_audit_event(
        signature_request_id=active_pending.id,
        event_type="late",
        actor_type="system",
    )
    early = repo.append_audit_event(
        signature_request_id=active_pending.id,
        event_type="early",
        actor_type="system",
    )
    late.occurred_at = now + timedelta(minutes=1)
    early.occurred_at = now - timedelta(minutes=1)
    test_db.commit()

    audit_events = repo.list_audit_events(active_pending.id)
    assert [event.event_type for event in audit_events] == ["early", "late"]


def test_repository_update_missing_id_and_pending_by_annual_report_and_repr(test_db):
    repo = SignatureRequestRepository(test_db)
    user = _user(test_db)
    client = _client(test_db, suffix="AR")

    assert repo.update(999999, status=SignatureRequestStatus.CANCELED) is None

    pending = repo.create(
        business_id=client.id,
        created_by=user.id,
        request_type=SignatureRequestType.ANNUAL_REPORT_APPROVAL,
        title="Annual Pending",
        signer_name="Signer A",
        annual_report_id=77,
    )
    draft = repo.create(
        business_id=client.id,
        created_by=user.id,
        request_type=SignatureRequestType.ANNUAL_REPORT_APPROVAL,
        title="Annual Draft",
        signer_name="Signer B",
        annual_report_id=77,
    )
    other = repo.create(
        business_id=client.id,
        created_by=user.id,
        request_type=SignatureRequestType.ANNUAL_REPORT_APPROVAL,
        title="Different Report",
        signer_name="Signer C",
        annual_report_id=88,
    )

    repo.update(pending.id, status=SignatureRequestStatus.PENDING_SIGNATURE)
    repo.update(other.id, status=SignatureRequestStatus.PENDING_SIGNATURE)

    annual_pending = repo.list_pending_by_annual_report(77)
    assert [item.id for item in annual_pending] == [pending.id]
    assert draft.id not in [item.id for item in annual_pending]

    model_repr = repr(
        SignatureRequest(
            id=123,
            business_id=456,
            created_by=user.id,
            request_type=SignatureRequestType.CUSTOM,
            title="Repr",
            signer_name="Signer",
            status=SignatureRequestStatus.DRAFT,
        )
    )
    audit_repr = repr(
        SignatureAuditEvent(
            id=321,
            signature_request_id=123,
            event_type="created",
            actor_type="advisor",
        )
    )
    assert "SignatureRequest(id=123" in model_repr
    assert "SignatureAuditEvent(id=321" in audit_repr
