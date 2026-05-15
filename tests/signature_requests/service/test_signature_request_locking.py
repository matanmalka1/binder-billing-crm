from datetime import date, timedelta

import pytest

from app.businesses.models.business import Business
from app.core.exceptions import AppError
from app.signature_requests.models.signature_request import SignatureRequestType
from app.signature_requests.repositories.signature_request_repository import (
    SignatureRequestRepository,
)
from app.signature_requests.services.signature_request_service import (
    SignatureRequestService,
)
from app.utils.time_utils import utcnow
from tests.helpers.identity import seed_client_with_business


def _business(db) -> Business:
    _client, business = seed_client_with_business(
        db,
        full_name="Signature Lock Client",
        id_number="999999998",
        business_name="Signature Lock Business",
        opened_at=date(2026, 1, 1),
    )
    db.commit()
    return business


def _create_pending_request(db, user_id=1):
    business = _business(db)
    return SignatureRequestRepository(db).create(
        client_record_id=business.client_id,
        business_id=business.id,
        created_by=user_id,
        request_type=SignatureRequestType.CUSTOM,
        title="Test Request",
        signer_name="Test Signer",
        signing_token=f"token-{business.id}",
        sent_at=utcnow(),
        expires_at=utcnow() + timedelta(days=14),
    )


def test_cancel_request_uses_locked_fetch(test_db, monkeypatch):
    req = _create_pending_request(test_db)
    svc = SignatureRequestService(test_db)

    calls = []
    original = svc.repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.repo,
        "get_by_id_for_update",
        lambda rid: calls.append(rid) or original(rid),
    )

    svc.cancel_request(request_id=req.id, canceled_by=1, canceled_by_name="Tester")
    assert req.id in calls


def test_sign_request_uses_locked_token_fetch(test_db, monkeypatch):
    req = _create_pending_request(test_db)
    token = req.signing_token
    svc = SignatureRequestService(test_db)

    calls = []
    original = svc.repo.get_by_token_for_update
    monkeypatch.setattr(
        svc.repo,
        "get_by_token_for_update",
        lambda t: calls.append(t) or original(t),
    )

    svc.sign_request(token=token)
    assert token in calls


def test_decline_request_uses_locked_token_fetch(test_db, monkeypatch):
    req = _create_pending_request(test_db)
    token = req.signing_token
    svc = SignatureRequestService(test_db)

    calls = []
    original = svc.repo.get_by_token_for_update
    monkeypatch.setattr(
        svc.repo,
        "get_by_token_for_update",
        lambda t: calls.append(t) or original(t),
    )

    svc.decline_request(token=token)
    assert token in calls


def test_cancel_already_canceled_raises(test_db):
    req = _create_pending_request(test_db)
    svc = SignatureRequestService(test_db)
    svc.cancel_request(request_id=req.id, canceled_by=1, canceled_by_name="Tester")

    with pytest.raises(AppError) as exc:
        svc.cancel_request(request_id=req.id, canceled_by=1, canceled_by_name="Tester")
    assert exc.value.code == "SIGNATURE_REQUEST.INVALID_STATUS"


def test_sign_already_signed_raises(test_db):
    req = _create_pending_request(test_db)
    token = req.signing_token
    svc = SignatureRequestService(test_db)
    svc.sign_request(token=token)

    with pytest.raises(AppError) as exc:
        svc.sign_request(token=token)
    assert exc.value.code == "SIGNATURE_REQUEST.TOKEN_INVALID"
