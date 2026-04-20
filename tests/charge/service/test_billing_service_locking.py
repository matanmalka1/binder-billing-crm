"""
Tests verifying that status-transition methods in BillingService use the
locked fetch path (get_by_id_for_update) and correctly enforce state guards.

Note: SQLite does not support real SELECT … FOR UPDATE blocking. These tests
verify *code path* (via monkeypatch spy) and *invalid-state* handling only.
True concurrent exclusion requires PostgreSQL with multiple connections.
"""
from datetime import date

import pytest

from app.businesses.models.business import Business, BusinessStatus
from app.charge.models.charge import ChargeStatus, ChargeType
from app.charge.repositories.charge_repository import ChargeRepository
from app.charge.services.billing_service import BillingService
from app.core.exceptions import AppError, ConflictError
from tests.helpers.identity import seed_client_with_business


def _business(db):
    _client, business = seed_client_with_business(
        db,
        full_name="Locking Test Client",
        id_number="LOCK001",
    )
    business.status = BusinessStatus.ACTIVE
    db.commit()
    return business


def _draft_charge(db, business):
    repo = ChargeRepository(db)
    return repo.create(
        client_record_id=business.client_id,
        business_id=business.id,
        amount=100.0,
        charge_type=ChargeType.OTHER,
    )


# ── Code-path verification ────────────────────────────────────────────────────

def test_issue_charge_uses_locked_fetch(test_db, monkeypatch):
    business = _business(test_db)
    charge = _draft_charge(test_db, business)
    svc = BillingService(test_db)

    calls = []
    original = svc.charge_repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.charge_repo, "get_by_id_for_update",
        lambda cid: calls.append(cid) or original(cid),
    )

    svc.issue_charge(charge.id, actor_id=1)
    assert charge.id in calls, "issue_charge must call get_by_id_for_update"


def test_mark_charge_paid_uses_locked_fetch(test_db, monkeypatch):
    business = _business(test_db)
    charge = _draft_charge(test_db, business)
    repo = ChargeRepository(test_db)
    repo.update_status(charge.id, ChargeStatus.ISSUED)
    svc = BillingService(test_db)

    calls = []
    original = svc.charge_repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.charge_repo, "get_by_id_for_update",
        lambda cid: calls.append(cid) or original(cid),
    )

    svc.mark_charge_paid(charge.id, actor_id=1)
    assert charge.id in calls, "mark_charge_paid must call get_by_id_for_update"


def test_cancel_charge_uses_locked_fetch(test_db, monkeypatch):
    business = _business(test_db)
    charge = _draft_charge(test_db, business)
    svc = BillingService(test_db)

    calls = []
    original = svc.charge_repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.charge_repo, "get_by_id_for_update",
        lambda cid: calls.append(cid) or original(cid),
    )

    svc.cancel_charge(charge.id, actor_id=1)
    assert charge.id in calls, "cancel_charge must call get_by_id_for_update"


# ── Invalid-state guard (sequential simulation of stale read) ─────────────────

def test_issue_charge_already_issued_raises(test_db):
    """Second issue on an already-ISSUED charge must fail — simulates the guard
    that prevents a race-winner's commit from being applied twice."""
    business = _business(test_db)
    charge = _draft_charge(test_db, business)
    svc = BillingService(test_db)
    svc.issue_charge(charge.id, actor_id=1)

    with pytest.raises(AppError) as exc:
        svc.issue_charge(charge.id, actor_id=1)
    assert exc.value.code == "CHARGE.INVALID_STATUS"


def test_mark_paid_already_paid_raises(test_db):
    business = _business(test_db)
    charge = _draft_charge(test_db, business)
    repo = ChargeRepository(test_db)
    repo.update_status(charge.id, ChargeStatus.ISSUED)
    svc = BillingService(test_db)
    svc.mark_charge_paid(charge.id, actor_id=1)

    with pytest.raises(AppError) as exc:
        svc.mark_charge_paid(charge.id, actor_id=1)
    assert exc.value.code == "CHARGE.INVALID_STATUS"


def test_cancel_already_canceled_raises(test_db):
    business = _business(test_db)
    charge = _draft_charge(test_db, business)
    svc = BillingService(test_db)
    svc.cancel_charge(charge.id, actor_id=1)

    with pytest.raises(ConflictError) as exc:
        svc.cancel_charge(charge.id, actor_id=1)
    assert exc.value.code == "CHARGE.CONFLICT"
