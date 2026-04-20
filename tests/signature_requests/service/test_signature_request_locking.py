"""
Tests verifying that signature request transition methods use the locked fetch
path and correctly enforce state guards.

Note: SQLite does not support real SELECT … FOR UPDATE blocking.
Tests verify code path (monkeypatch spy) and invalid-state handling only.
"""
from datetime import date
from types import SimpleNamespace

import pytest

from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.core.exceptions import AppError
from app.signature_requests.models.signature_request import SignatureRequestStatus, SignatureRequestType
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.signature_request_service import SignatureRequestService


def _business(db) -> Business:
    client = Client(full_name="Signature Lock Client", id_number="999999998")
    db.add(client)
    db.flush()
    business = Business(client_id=client.id, business_name="Signature Lock Business", opened_at=date(2026, 1, 1))
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _create_draft_request(db, user_id=1):
    business = _business(db)
    repo = SignatureRequestRepository(db)
    return repo.create(
        client_id=business.client_id,
        client_record_id=business.client_id,
        business_id=business.id,
        created_by=user_id,
        request_type=SignatureRequestType.CUSTOM,
        title="Test Request",
        signer_name="Test Signer",
    )


def _send_request(db, request_id, user_id=1):
    svc = SignatureRequestService(db)
    return svc.send_request(
        request_id=request_id,
        sent_by=user_id,
        sent_by_name="Tester",
    )


# ── Code-path verification ────────────────────────────────────────────────────

def test_send_request_uses_locked_fetch(test_db, monkeypatch):
    req = _create_draft_request(test_db)
    svc = SignatureRequestService(test_db)

    calls = []
    original = svc.repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.repo, "get_by_id_for_update",
        lambda rid: calls.append(rid) or original(rid),
    )

    svc.send_request(request_id=req.id, sent_by=1, sent_by_name="Tester")
    assert req.id in calls, "send_request must call get_by_id_for_update"


def test_cancel_request_uses_locked_fetch(test_db, monkeypatch):
    req = _create_draft_request(test_db)
    svc = SignatureRequestService(test_db)

    calls = []
    original = svc.repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.repo, "get_by_id_for_update",
        lambda rid: calls.append(rid) or original(rid),
    )

    svc.cancel_request(request_id=req.id, canceled_by=1, canceled_by_name="Tester")
    assert req.id in calls, "cancel_request must call get_by_id_for_update"


def test_sign_request_uses_locked_token_fetch(test_db, monkeypatch):
    req = _create_draft_request(test_db)
    sent = _send_request(test_db, req.id)
    token = sent.signing_token
    svc = SignatureRequestService(test_db)

    calls = []
    original = svc.repo.get_by_token_for_update
    monkeypatch.setattr(
        svc.repo, "get_by_token_for_update",
        lambda t: calls.append(t) or original(t),
    )

    svc.sign_request(token=token)
    assert token in calls, "sign_request must call get_by_token_for_update"


def test_decline_request_uses_locked_token_fetch(test_db, monkeypatch):
    req = _create_draft_request(test_db)
    sent = _send_request(test_db, req.id)
    token = sent.signing_token
    svc = SignatureRequestService(test_db)

    calls = []
    original = svc.repo.get_by_token_for_update
    monkeypatch.setattr(
        svc.repo, "get_by_token_for_update",
        lambda t: calls.append(t) or original(t),
    )

    svc.decline_request(token=token)
    assert token in calls, "decline_request must call get_by_token_for_update"


# ── Invalid-state guard ───────────────────────────────────────────────────────

def test_send_already_pending_raises(test_db):
    req = _create_draft_request(test_db)
    _send_request(test_db, req.id)

    with pytest.raises(AppError) as exc:
        _send_request(test_db, req.id)
    assert exc.value.code == "SIGNATURE_REQUEST.INVALID_STATUS"


def test_cancel_already_canceled_raises(test_db):
    req = _create_draft_request(test_db)
    svc = SignatureRequestService(test_db)
    svc.cancel_request(request_id=req.id, canceled_by=1, canceled_by_name="Tester")

    with pytest.raises(AppError) as exc:
        svc.cancel_request(request_id=req.id, canceled_by=1, canceled_by_name="Tester")
    assert exc.value.code == "SIGNATURE_REQUEST.INVALID_STATUS"


def test_sign_already_signed_raises(test_db):
    req = _create_draft_request(test_db)
    sent = _send_request(test_db, req.id)
    token = sent.signing_token
    svc = SignatureRequestService(test_db)
    svc.sign_request(token=token)

    # Token is cleared after signing — second attempt raises token-invalid
    with pytest.raises(AppError) as exc:
        svc.sign_request(token=token)
    assert exc.value.code == "SIGNATURE_REQUEST.TOKEN_INVALID"
