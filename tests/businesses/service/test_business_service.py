from datetime import date
from types import SimpleNamespace

import pytest

from app.businesses.models.business import BusinessStatus
from app.businesses.services.business_service import BusinessService
from app.core.exceptions import ConflictError, ForbiddenError
from app.users.models.user import UserRole


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
            business_type="company",
            opened_at=date(2026, 1, 1),
            business_name="Dup Name",
        )

    assert exc.value.code == "BUSINESS.NAME_CONFLICT"


def test_update_business_blocks_non_advisor_freeze_or_close(test_db):
    service = BusinessService(test_db)
    service.business_repo = SimpleNamespace(get_by_id=lambda _business_id: object())

    with pytest.raises(ForbiddenError) as exc:
        service.update_business(
            business_id=3,
            user_role=UserRole.SECRETARY,
            status=BusinessStatus.CLOSED.value,
        )

    assert exc.value.code == "BUSINESS.FORBIDDEN"


def test_update_business_sets_closed_at_for_close_action(test_db):
    captured = {}

    def _update(_business_id, **fields):
        captured.update(fields)
        return fields

    service = BusinessService(test_db)
    service.business_repo = SimpleNamespace(
        get_by_id=lambda _business_id: object(),
        update=_update,
    )

    result = service.update_business(
        business_id=9,
        user_role=UserRole.ADVISOR,
        status=BusinessStatus.CLOSED.value,
    )

    assert result["status"] == BusinessStatus.CLOSED
    assert isinstance(result["closed_at"], date)
    assert isinstance(captured["closed_at"], date)
