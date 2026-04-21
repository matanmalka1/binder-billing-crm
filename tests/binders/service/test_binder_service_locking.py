"""
Tests verifying that BinderService transition methods use the locked fetch
path (get_by_id_for_update) and correctly enforce state guards.

Note: SQLite does not support real SELECT … FOR UPDATE blocking.
Tests verify code path (monkeypatch spy) and invalid-state handling only.
"""
from datetime import date

import pytest

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.binder_service import BinderService
from app.core.exceptions import AppError
from tests.helpers.identity import seed_client_identity


def _create_client(db):
    return seed_client_identity(db, full_name="Locking Binder Client", id_number="BINLOCK001")


def _create_binder(db, client_id, status=BinderStatus.IN_OFFICE):
    repo = BinderRepository(db)
    binder = repo.create(
        client_record_id=client_id,
        binder_number=f"BIN-LOCK-{client_id}",
        period_start=date(2024, 1, 1),
        created_by=1,
    )
    if status != BinderStatus.IN_OFFICE:
        binder.status = status
        db.commit()
        db.refresh(binder)
    return binder


# ── Code-path verification ────────────────────────────────────────────────────

def test_mark_ready_for_pickup_uses_locked_fetch(test_db, test_user, monkeypatch):
    client = _create_client(test_db)
    binder = _create_binder(test_db, client.id)
    svc = BinderService(test_db)

    calls = []
    original = svc.binder_repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.binder_repo, "get_by_id_for_update",
        lambda bid: calls.append(bid) or original(bid),
    )

    svc.mark_ready_for_pickup(binder.id, user_id=test_user.id)
    assert binder.id in calls, "mark_ready_for_pickup must call get_by_id_for_update"


def test_return_binder_uses_locked_fetch(test_db, test_user, monkeypatch):
    client = _create_client(test_db)
    binder = _create_binder(test_db, client.id, BinderStatus.READY_FOR_PICKUP)
    svc = BinderService(test_db)

    calls = []
    original = svc.binder_repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.binder_repo, "get_by_id_for_update",
        lambda bid: calls.append(bid) or original(bid),
    )

    svc.return_binder(binder.id, pickup_person_name="Test Person", returned_by=test_user.id)
    assert binder.id in calls, "return_binder must call get_by_id_for_update"


def test_revert_ready_uses_locked_fetch(test_db, test_user, monkeypatch):
    client = _create_client(test_db)
    binder = _create_binder(test_db, client.id, BinderStatus.READY_FOR_PICKUP)
    svc = BinderService(test_db)

    calls = []
    original = svc.binder_repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.binder_repo, "get_by_id_for_update",
        lambda bid: calls.append(bid) or original(bid),
    )

    svc.revert_ready(binder.id, user_id=test_user.id)
    assert binder.id in calls, "revert_ready must call get_by_id_for_update"


# ── Invalid-state guard ───────────────────────────────────────────────────────

def test_mark_ready_already_ready_raises(test_db, test_user):
    client = _create_client(test_db)
    binder = _create_binder(test_db, client.id, BinderStatus.READY_FOR_PICKUP)
    svc = BinderService(test_db)

    with pytest.raises(AppError):
        svc.mark_ready_for_pickup(binder.id, user_id=test_user.id)


def test_revert_ready_from_wrong_status_raises(test_db, test_user):
    client = _create_client(test_db)
    binder = _create_binder(test_db, client.id, BinderStatus.IN_OFFICE)
    svc = BinderService(test_db)

    with pytest.raises(AppError):
        svc.revert_ready(binder.id, user_id=test_user.id)
