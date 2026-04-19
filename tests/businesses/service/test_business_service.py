from datetime import date
from types import SimpleNamespace

import pytest

from app.businesses.models.business import Business, BusinessStatus
from app.businesses.services.business_service import BusinessService
from app.clients.models.client import Client
from app.core.exceptions import ConflictError, ForbiddenError
from app.users.models.user import UserRole


def _create_business_row(test_db, *, status: BusinessStatus = BusinessStatus.ACTIVE) -> Business:
    client = Client(full_name="Service Test Client", id_number="BS-001")
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name="Service Test Business",
        opened_at=date(2026, 1, 1),
        status=status,
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_create_business_rejects_duplicate_name_for_client(test_db):
    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: object())
    service.business_repo = SimpleNamespace(
        all_non_deleted_are_closed=lambda _client_id: False,
        list_by_client=lambda _client_id, **_kwargs: [SimpleNamespace(business_name="Dup Name")]
    )

    with pytest.raises(ConflictError) as exc:
        service.create_business(
            client_id=1,
            opened_at=date(2026, 1, 1),
            business_name="Dup Name",
        )

    assert exc.value.code == "BUSINESS.NAME_CONFLICT"


def test_create_business_defaults_opened_at_to_today(monkeypatch, test_db):
    captured = {}
    generated = {}

    def _create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=12, **kwargs)

    service = BusinessService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _client_id: SimpleNamespace())
    service.business_repo = SimpleNamespace(
        all_non_deleted_are_closed=lambda _client_id: False,
        list_by_client=lambda _client_id, **_kwargs: [],
        create=_create,
    )
    monkeypatch.setattr(
        "app.businesses.services.business_service.generate_client_obligations",
        lambda db, client_id, **kwargs: generated.update({"db": db, "client_id": client_id, **kwargs}),
    )

    result = service.create_business(
        client_id=1,
        business_name="From Client Date",
    )

    assert result.opened_at == date.today()
    assert captured["opened_at"] == date.today()
    assert generated["client_id"] == 1
    assert generated["best_effort"] is False


def test_update_business_blocks_non_advisor_freeze_or_close(test_db):
    business = _create_business_row(test_db)
    service = BusinessService(test_db)

    with pytest.raises(ForbiddenError) as exc:
        service.update_business(
            business_id=business.id,
            client_id=business.client_id,
            user_role=UserRole.SECRETARY,
            status=BusinessStatus.CLOSED.value,
        )

    assert exc.value.code == "BUSINESS.FORBIDDEN"


def test_update_business_sets_closed_at_for_close_action(test_db):
    business = _create_business_row(test_db)
    service = BusinessService(test_db)

    result = service.update_business(
        business_id=business.id,
        client_id=business.client_id,
        user_role=UserRole.ADVISOR,
        status=BusinessStatus.CLOSED.value,
    )

    assert result.status == BusinessStatus.CLOSED
    assert isinstance(result.closed_at, date)
