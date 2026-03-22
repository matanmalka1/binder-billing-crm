from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.businesses.models.business import BusinessStatus
from app.businesses.services.business_service import BusinessService
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.users.models.user import UserRole


def test_create_business_raises_not_found_when_client_missing(test_db):
    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: None)

    with pytest.raises(NotFoundError) as exc:
        service.create_business(
            client_id=99,
            business_type="company",
            opened_at=date(2026, 1, 1),
        )

    assert exc.value.code == "CLIENT.NOT_FOUND"


def test_create_business_maps_integrity_error_to_conflict(test_db):
    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: object())
    service.business_repo = SimpleNamespace(
        list_by_client=lambda _client_id: [],
        create=lambda **_kwargs: (_ for _ in ()).throw(IntegrityError("stmt", "params", Exception("db"))),
    )

    with pytest.raises(ConflictError) as exc:
        service.create_business(
            client_id=1,
            business_type="company",
            opened_at=date(2026, 1, 1),
            business_name="Dup",
        )

    assert exc.value.code == "BUSINESS.CONFLICT"


def test_update_business_rejects_invalid_status_value(test_db):
    service = BusinessService(test_db)
    service.business_repo = SimpleNamespace(get_by_id=lambda _business_id: object())

    with pytest.raises(AppError) as exc:
        service.update_business(
            business_id=10,
            user_role=UserRole.ADVISOR,
            status="not-a-real-status",
        )

    assert exc.value.code == "BUSINESS.INVALID_STATUS"


def test_delete_business_raises_when_missing(test_db):
    service = BusinessService(test_db)
    service.business_repo = SimpleNamespace(get_by_id=lambda _business_id: None)

    with pytest.raises(NotFoundError) as exc:
        service.delete_business(123, actor_id=1)

    assert exc.value.code == "BUSINESS.NOT_FOUND"


def test_restore_business_requires_advisor_role(test_db):
    service = BusinessService(test_db)

    with pytest.raises(ForbiddenError) as exc:
        service.restore_business(1, actor_id=5, actor_role=UserRole.SECRETARY)

    assert exc.value.code == "BUSINESS.FORBIDDEN"


def test_restore_business_not_deleted_raises_conflict(test_db):
    service = BusinessService(test_db)
    service.business_repo = SimpleNamespace(
        get_by_id_including_deleted=lambda _business_id: SimpleNamespace(deleted_at=None)
    )

    with pytest.raises(ConflictError) as exc:
        service.restore_business(1, actor_id=5, actor_role=UserRole.ADVISOR)

    assert exc.value.code == "BUSINESS.NOT_DELETED"


def test_restore_business_raises_when_repo_restore_returns_none(test_db):
    service = BusinessService(test_db)
    service.business_repo = SimpleNamespace(
        get_by_id_including_deleted=lambda _business_id: SimpleNamespace(deleted_at=date(2026, 1, 1)),
        restore=lambda _business_id, restored_by: None,
    )

    with pytest.raises(NotFoundError) as exc:
        service.restore_business(2, actor_id=5, actor_role=UserRole.ADVISOR)

    assert exc.value.code == "BUSINESS.NOT_FOUND"


def test_bulk_update_status_delegates_to_bulk_service(test_db):
    service = BusinessService(test_db)
    service._bulk = SimpleNamespace(
        bulk_update_status=lambda **kwargs: ([1], [{"id": 2, "error": "x"}])
    )

    succeeded, failed = service.bulk_update_status(
        business_ids=[1, 2],
        action="freeze",
        actor_id=10,
        actor_role=UserRole.ADVISOR,
    )

    assert succeeded == [1]
    assert failed == [{"id": 2, "error": "x"}]


def test_get_business_or_raise_delegates_lookup_function(monkeypatch, test_db):
    service = BusinessService(test_db)
    expected = object()
    monkeypatch.setattr(
        "app.businesses.services.business_service._get_or_raise",
        lambda db, business_id: expected,
    )

    assert service.get_business_or_raise(7) is expected


def test_list_businesses_for_client_raises_when_client_missing(test_db):
    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: None)

    with pytest.raises(NotFoundError) as exc:
        service.list_businesses_for_client(777)

    assert exc.value.code == "CLIENT.NOT_FOUND"


def test_list_businesses_delegates_to_bulk_service(test_db):
    service = BusinessService(test_db)
    expected = ([SimpleNamespace(id=5)], 1)
    service._bulk = SimpleNamespace(list_businesses=lambda **_kwargs: expected)

    assert service.list_businesses(status="active") == expected

