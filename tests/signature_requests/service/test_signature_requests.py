from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.clients.models import Client
from app.signature_requests.models.signature_request import SignatureRequestStatus, SignatureRequestType
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services import SignatureRequestService
from app.signature_requests.services import create_request as create_request_module
from app.signature_requests.services import signature_request_validations as validations
from app.signature_requests.services.admin_actions import expire_overdue_requests
from app.core.exceptions import AppError, NotFoundError
from app.utils.time_utils import utcnow


def _client(db) -> Client:
    client = Client(
        full_name="Signature Service Client",
        id_number="999999992",
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
        business_id=client.id,
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
        business_id=client.id,
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


def test_list_business_requests_invalid_status_raises_app_error(test_db, test_user):
    client = _client(test_db)
    service = SignatureRequestService(test_db)

    with pytest.raises(AppError) as exc_info:
        service.list_business_requests(business_id=client.id, status="not_a_status")

    assert exc_info.value.code == "SIGNATURE_REQUEST.INVALID_STATUS"


def test_service_get_by_token_returns_request(test_db, test_user):
    client = _client(test_db)
    repo = SignatureRequestRepository(test_db)
    req = repo.create(
        business_id=client.id,
        created_by=test_user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Token Lookup",
        signer_name="Signer",
    )
    repo.update(req.id, signing_token="lookup-token")

    found = SignatureRequestService(test_db).get_by_token("lookup-token")

    assert found is not None
    assert found.id == req.id


def test_service_expire_overdue_requests_delegates_and_returns_count(test_db, test_user):
    client = _client(test_db)
    repo = SignatureRequestRepository(test_db)
    req = repo.create(
        business_id=client.id,
        created_by=test_user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Service Expire",
        signer_name="Late Signer",
    )
    repo.update(
        req.id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token="service-expire-token",
        sent_at=utcnow() - timedelta(days=10),
        expires_at=utcnow() - timedelta(days=1),
    )

    count = SignatureRequestService(test_db).expire_overdue_requests()
    refreshed = repo.get_by_id(req.id)

    assert count == 1
    assert refreshed.status == SignatureRequestStatus.EXPIRED


def test_create_request_raises_when_business_missing():
    repo = SimpleNamespace(
        create=lambda **kwargs: None,
        append_audit_event=lambda **kwargs: None,
    )
    business_repo = SimpleNamespace(get_by_id=lambda _business_id: None)

    with pytest.raises(NotFoundError) as exc_info:
        create_request_module.create_request(
            repo,
            business_repo,
            business_id=123,
            created_by=1,
            created_by_name="Advisor",
            request_type="custom",
            title="Missing business",
            signer_name="Signer",
        )

    assert exc_info.value.code == "BUSINESS.NOT_FOUND"


def test_create_request_raises_on_invalid_type():
    repo = SimpleNamespace(
        create=lambda **kwargs: None,
        append_audit_event=lambda **kwargs: None,
    )
    business_repo = SimpleNamespace(get_by_id=lambda _business_id: SimpleNamespace(email=None, phone=None))

    with pytest.raises(AppError) as exc_info:
        create_request_module.create_request(
            repo,
            business_repo,
            business_id=1,
            created_by=1,
            created_by_name="Advisor",
            request_type="not-a-valid-type",
            title="Bad type",
            signer_name="Signer",
        )

    assert exc_info.value.code == "SIGNATURE_REQUEST.INVALID_TYPE"


def test_create_request_falls_back_to_business_contact_details():
    captured = {}

    def _create(**kwargs):
        captured["create"] = kwargs
        return SimpleNamespace(id=42)

    def _append_audit_event(**kwargs):
        captured["audit"] = kwargs

    repo = SimpleNamespace(
        create=_create,
        append_audit_event=_append_audit_event,
    )
    business_repo = SimpleNamespace(
        get_by_id=lambda _business_id: SimpleNamespace(email="biz@example.com", phone="050-1111111")
    )

    create_request_module.create_request(
        repo,
        business_repo,
        business_id=1,
        created_by=9,
        created_by_name="Advisor",
        request_type="custom",
        title="Fallback contact",
        signer_name="Signer",
        signer_email=None,
        signer_phone=None,
    )

    assert captured["create"]["signer_email"] == "biz@example.com"
    assert captured["create"]["signer_phone"] == "050-1111111"
    assert captured["audit"]["event_type"] == "created"


def test_cancel_request_rejects_non_cancelable_status(test_db, test_user):
    client = _client(test_db)
    repo = SignatureRequestRepository(test_db)
    req = repo.create(
        business_id=client.id,
        created_by=test_user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Already signed",
        signer_name="Signer",
    )
    repo.update(req.id, status=SignatureRequestStatus.SIGNED)

    with pytest.raises(AppError) as exc_info:
        SignatureRequestService(test_db).cancel_request(
            request_id=req.id,
            canceled_by=test_user.id,
            canceled_by_name=test_user.full_name,
            reason="Cancel after sign",
        )

    assert exc_info.value.code == "SIGNATURE_REQUEST.INVALID_STATUS"


def test_get_or_raise_and_assert_signable_validation_branches(test_db, test_user):
    repo = SignatureRequestRepository(test_db)
    client = _client(test_db)
    req = repo.create(
        business_id=client.id,
        created_by=test_user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Validation",
        signer_name="Signer",
    )

    with pytest.raises(NotFoundError) as not_found_exc:
        validations.get_or_raise(repo, 999999)
    assert not_found_exc.value.code == "SIGNATURE_REQUEST.NOT_FOUND"

    with pytest.raises(AppError) as invalid_status_exc:
        validations.assert_signable(repo, req)
    assert invalid_status_exc.value.code == "SIGNATURE_REQUEST.INVALID_STATUS"
