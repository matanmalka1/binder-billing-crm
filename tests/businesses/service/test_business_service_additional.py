from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch

from app.audit.constants import ACTION_RESTORED, ENTITY_BUSINESS
from app.audit.models.entity_audit_log import EntityAuditLog
from app.businesses.models.business import Business, BusinessStatus
from app.businesses.services.business_service import BusinessService
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.utils.time_utils import utcnow
from app.users.models.user import UserRole
from tests.helpers.identity import seed_client_identity


def _create_business_row(
    test_db,
    *,
    status: BusinessStatus = BusinessStatus.ACTIVE,
    legal_entity_id: int | None = None,
) -> Business:
    business = Business(
        business_name="Additional Service Business",
        opened_at=date(2026, 1, 1),
        status=status,
        legal_entity_id=legal_entity_id,
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_create_business_raises_not_found_when_client_missing(test_db):
    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: None)

    with pytest.raises(NotFoundError) as exc:
        service.create_business(
            client_id=99,
            opened_at=date(2026, 1, 1),
        )

    assert exc.value.code == "CLIENT.NOT_FOUND"


def test_create_business_maps_integrity_error_to_conflict(test_db):
    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: object())
    service.business_repo = SimpleNamespace(
        all_non_deleted_are_closed=lambda _client_id: False,
        list_by_client=lambda _client_id, **_kwargs: [],
        create=lambda **_kwargs: (_ for _ in ()).throw(IntegrityError("stmt", "params", Exception("db"))),
    )

    with pytest.raises(ConflictError) as exc:
        service.create_business(
            client_id=1,
            opened_at=date(2026, 1, 1),
            business_name="Dup",
        )

    assert exc.value.code == "BUSINESS.CONFLICT"


def test_create_business_defaults_opened_at_to_today_when_missing_everywhere(monkeypatch, test_db):
    captured = {}

    def _create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=15, **kwargs)

    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: SimpleNamespace())
    service.business_repo = SimpleNamespace(
        all_non_deleted_are_closed=lambda _client_id: False,
        list_by_client=lambda _client_id, **_kwargs: [],
        create=_create,
    )

    with patch("app.businesses.services.business_service.date") as mock_date:
        mock_date.today.return_value = date(2026, 4, 9)
        result = service.create_business(
            client_id=1,
            business_name="Uses Today",
        )

    assert result.opened_at == date(2026, 4, 9)
    assert captured["opened_at"] == date(2026, 4, 9)


def test_update_business_rejects_invalid_status_value(test_db):
    client = seed_client_identity(test_db, full_name="Additional Client", id_number="BADD001")
    business = _create_business_row(test_db, legal_entity_id=client.legal_entity_id)
    service = BusinessService(test_db)

    with pytest.raises(AppError) as exc:
        service.update_business(
            business_id=business.id,
            client_id=client.id,
            user_role=UserRole.ADVISOR,
            status="not-a-real-status",
        )

    assert exc.value.code == "BUSINESS.INVALID_STATUS"


def test_update_business_rejects_wrong_client_id(test_db):
    client = seed_client_identity(test_db, full_name="Additional Client", id_number="BADD002")
    business = _create_business_row(test_db, legal_entity_id=client.legal_entity_id)
    service = BusinessService(test_db)

    with pytest.raises(NotFoundError) as exc:
        service.update_business(
            business_id=business.id,
            client_id=1 + 999,
            user_role=UserRole.ADVISOR,
            status=BusinessStatus.ACTIVE.value,
        )

    assert exc.value.code == "BUSINESS.NOT_FOUND"


def test_update_business_to_active_clears_closed_at(test_db):
    client = seed_client_identity(test_db, full_name="Additional Client", id_number="BADD003")
    business = _create_business_row(
        test_db,
        status=BusinessStatus.CLOSED,
        legal_entity_id=client.legal_entity_id,
    )
    business.closed_at = date(2026, 2, 1)
    test_db.commit()

    result = BusinessService(test_db).update_business(
        business_id=business.id,
        client_id=client.id,
        user_role=UserRole.ADVISOR,
        status=BusinessStatus.ACTIVE.value,
    )

    assert result.status == BusinessStatus.ACTIVE
    assert result.closed_at is None


def test_delete_business_raises_when_missing(test_db):
    service = BusinessService(test_db)

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
    service._lifecycle.business_repo = SimpleNamespace(
        get_by_id_including_deleted=lambda _business_id: SimpleNamespace(deleted_at=None)
    )

    with pytest.raises(ConflictError) as exc:
        service.restore_business(1, actor_id=5, actor_role=UserRole.ADVISOR)

    assert exc.value.code == "BUSINESS.NOT_DELETED"


def test_restore_business_raises_when_repo_restore_returns_none(test_db):
    service = BusinessService(test_db)
    service._lifecycle.business_repo = SimpleNamespace(
        get_by_id_including_deleted=lambda _business_id: SimpleNamespace(
            deleted_at=date(2026, 1, 1),
        ),
        restore=lambda _business_id, restored_by: None,
    )

    with pytest.raises(NotFoundError) as exc:
        service.restore_business(2, actor_id=5, actor_role=UserRole.ADVISOR)

    assert exc.value.code == "BUSINESS.NOT_FOUND"


def test_restore_business_restores_soft_deleted_business_and_writes_audit(test_db):
    business = _create_business_row(test_db, status=BusinessStatus.CLOSED)
    business.deleted_at = utcnow()
    business.deleted_by = 4
    test_db.commit()

    restored = BusinessService(test_db).restore_business(
        business.id,
        actor_id=9,
        actor_role=UserRole.ADVISOR,
    )

    assert restored.id == business.id
    assert restored.deleted_at is None
    assert restored.status == BusinessStatus.ACTIVE
    assert restored.restored_by == 9

    audit = (
        test_db.query(EntityAuditLog)
        .filter(
            EntityAuditLog.entity_type == ENTITY_BUSINESS,
            EntityAuditLog.entity_id == business.id,
            EntityAuditLog.action == ACTION_RESTORED,
        )
        .one()
    )
    assert audit.performed_by == 9


def test_get_business_or_raise_reads_from_business_repository(test_db):
    service = BusinessService(test_db)
    expected = object()
    service.business_repo = SimpleNamespace(
        get_by_id=lambda business_id: expected if business_id == 7 else None,
    )

    assert service.get_business_or_raise(7) is expected


def test_list_businesses_for_client_raises_when_client_missing(test_db):
    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: None)

    with pytest.raises(NotFoundError) as exc:
        service.list_businesses_for_client(777)

    assert exc.value.code == "CLIENT.NOT_FOUND"


def test_list_businesses_for_client_delegates_to_repository(test_db):
    service = BusinessService(test_db)
    client = SimpleNamespace(id=2)
    expected_items = [SimpleNamespace(id=5)]
    service.client_repo = SimpleNamespace(get_by_id=lambda client_id: client if client_id == 2 else None)
    service.business_repo = SimpleNamespace(
        list_by_client=lambda client_id, page, page_size: expected_items
        if (client_id, page, page_size) == (2, 3, 10)
        else [],
        count_by_client=lambda client_id: 1 if client_id == 2 else 0,
    )

    assert service.list_businesses_for_client(2, page=3, page_size=10) == (expected_items, 1)
