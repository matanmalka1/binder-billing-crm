from datetime import date, timedelta

import pytest

from app.clients.models import Client, ClientType
from app.signature_requests.models.signature_request import SignatureRequestStatus, SignatureRequestType
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services import SignatureRequestService
from app.signature_requests.services.admin_actions import expire_overdue_requests
from app.core.exceptions import AppError
from app.utils.time import utcnow


def _client(db) -> Client:
    client = Client(
        full_name="Signature Service Client",
        id_number="999999992",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
        email="svc@example.com",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_expire_overdue_requests_marks_expired_and_audits(test_db, test_user):
    client = _client(test_db)
    repo = SignatureRequestRepository(test_db)

    req = repo.create(
        client_id=client.id,
        created_by=test_user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Expired",
        signer_name="Late Signer",
    )
    # Force pending + expired
    repo.update(
        req.id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token="expired-token",
        sent_at=utcnow() - timedelta(days=10),
        expires_at=utcnow() - timedelta(days=1),
    )

    expired_count = expire_overdue_requests(repo)

    updated = repo.get_by_id(req.id)
    assert expired_count == 1
    assert updated.status == SignatureRequestStatus.EXPIRED
    assert updated.signing_token is None

    audit_events = repo.list_audit_events(req.id)
    assert any(e.event_type == "expired" for e in audit_events)


def test_record_view_on_expired_request_sets_status_and_raises(test_db, test_user):
    client = _client(test_db)
    repo = SignatureRequestRepository(test_db)
    req = repo.create(
        client_id=client.id,
        created_by=test_user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Expired View",
        signer_name="Viewer",
    )
    repo.update(
        req.id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token="view-token",
        sent_at=utcnow() - timedelta(days=5),
        expires_at=utcnow() - timedelta(days=1),
    )

    with pytest.raises(AppError) as exc_info:
        SignatureRequestService(test_db).record_view(token="view-token")

    assert exc_info.value.code == "SIGNATURE_REQUEST.EXPIRED"
    refreshed = repo.get_by_id(req.id)
    assert refreshed.status == SignatureRequestStatus.EXPIRED


def test_list_client_requests_invalid_status_raises_app_error(test_db, test_user):
    client = _client(test_db)
    service = SignatureRequestService(test_db)

    with pytest.raises(AppError) as exc_info:
        service.list_client_requests(client_id=client.id, status="not_a_status")

    assert exc_info.value.code == "SIGNATURE_REQUEST.INVALID_STATUS"
