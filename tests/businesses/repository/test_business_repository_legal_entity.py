"""Tests for legal_entity_id-based query methods on BusinessRepository."""
from datetime import date

import pytest

from app.businesses.models.business import Business, BusinessStatus
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType


@pytest.fixture()
def repo(test_db):
    return BusinessRepository(test_db)


@pytest.fixture()
def legal_entity(test_db):
    le = LegalEntity(id_number="LE-001", id_number_type=IdNumberType.INDIVIDUAL, official_name="Test Entity")
    test_db.add(le)
    test_db.flush()
    return le


_biz_counter = 0


def _make_business(db, legal_entity_id, *, status=BusinessStatus.ACTIVE, deleted=False):
    global _biz_counter
    _biz_counter += 1
    b = Business(
        legal_entity_id=legal_entity_id,
        business_name=f"Biz-{_biz_counter}",
        status=status,
        opened_at=date(2024, 1, 1),
    )
    if deleted:
        from app.utils.time_utils import utcnow
        b.deleted_at = utcnow()
    db.add(b)
    db.flush()
    return b


# ─── exists_for_legal_entity ────────────────────────────────────────────────

def test_exists_for_legal_entity_true(test_db, repo, legal_entity):
    _make_business(test_db, legal_entity.id)
    assert repo.exists_for_legal_entity(legal_entity.id) is True


def test_exists_for_legal_entity_false_when_deleted(test_db, repo, legal_entity):
    _make_business(test_db, legal_entity.id, deleted=True)
    assert repo.exists_for_legal_entity(legal_entity.id) is False


def test_exists_for_legal_entity_false_when_none(repo, legal_entity):
    assert repo.exists_for_legal_entity(legal_entity.id) is False


# ─── all_non_deleted_are_closed_for_legal_entity ────────────────────────────

def test_all_non_deleted_are_closed_for_legal_entity_true(test_db, repo, legal_entity):
    _make_business(test_db, legal_entity.id, status=BusinessStatus.CLOSED)
    assert repo.all_non_deleted_are_closed_for_legal_entity(legal_entity.id) is True


def test_all_non_deleted_are_closed_for_legal_entity_false_when_active(test_db, repo, legal_entity):
    _make_business(test_db, legal_entity.id, status=BusinessStatus.ACTIVE)
    assert repo.all_non_deleted_are_closed_for_legal_entity(legal_entity.id) is False


def test_all_non_deleted_are_closed_for_legal_entity_false_when_empty(repo, legal_entity):
    assert repo.all_non_deleted_are_closed_for_legal_entity(legal_entity.id) is False


# ─── get_ids_by_legal_entity ────────────────────────────────────────────────

def test_get_ids_by_legal_entity_returns_ids(test_db, repo, legal_entity):
    b1 = _make_business(test_db, legal_entity.id)
    b2 = _make_business(test_db, legal_entity.id)
    _make_business(test_db, legal_entity.id, deleted=True)
    ids = repo.get_ids_by_legal_entity(legal_entity.id)
    assert set(ids) == {b1.id, b2.id}


# ─── list_by_legal_entity ───────────────────────────────────────────────────

def test_list_by_legal_entity_returns_active(test_db, repo, legal_entity):
    b = _make_business(test_db, legal_entity.id)
    _make_business(test_db, legal_entity.id, deleted=True)
    result = repo.list_by_legal_entity(legal_entity.id)
    assert [r.id for r in result] == [b.id]


def test_list_by_legal_entity_empty(repo, legal_entity):
    assert repo.list_by_legal_entity(legal_entity.id) == []


# ─── count_by_legal_entity ──────────────────────────────────────────────────

def test_count_by_legal_entity(test_db, repo, legal_entity):
    _make_business(test_db, legal_entity.id)
    _make_business(test_db, legal_entity.id)
    _make_business(test_db, legal_entity.id, deleted=True)
    assert repo.count_by_legal_entity(legal_entity.id) == 2


# ─── list_by_legal_entity_including_deleted ─────────────────────────────────

def test_list_by_legal_entity_including_deleted(test_db, repo, legal_entity):
    b_active = _make_business(test_db, legal_entity.id)
    b_deleted = _make_business(test_db, legal_entity.id, deleted=True)
    result = repo.list_by_legal_entity_including_deleted(legal_entity.id)
    assert {r.id for r in result} == {b_active.id, b_deleted.id}


# ─── list_by_legal_entity_ids ───────────────────────────────────────────────

def test_list_by_legal_entity_ids_returns_matching(test_db, repo, legal_entity):
    le2 = LegalEntity(id_number="LE-002", id_number_type=IdNumberType.INDIVIDUAL, official_name="Test Entity 2")
    test_db.add(le2)
    test_db.flush()

    b1 = _make_business(test_db, legal_entity.id)
    b2 = _make_business(test_db, le2.id)
    _make_business(test_db, legal_entity.id, deleted=True)

    result = repo.list_by_legal_entity_ids([legal_entity.id, le2.id])
    assert {r.id for r in result} == {b1.id, b2.id}


def test_list_by_legal_entity_ids_empty_input(repo):
    assert repo.list_by_legal_entity_ids([]) == []
