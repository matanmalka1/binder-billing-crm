import pytest
from types import SimpleNamespace

from app.businesses.models.business import BusinessStatus
from app.businesses.services.business_guards import (
    assert_business_allows_create,
    assert_business_not_closed,
    validate_business_for_create,
)
from app.core.exceptions import ForbiddenError, NotFoundError


class _Business:
    def __init__(self, status):
        self.status = status


def test_assert_business_allows_create_allows_active():
    assert_business_allows_create(_Business(BusinessStatus.ACTIVE))


def test_assert_business_allows_create_blocks_closed_and_frozen():
    with pytest.raises(ForbiddenError) as closed:
        assert_business_allows_create(_Business(BusinessStatus.CLOSED))
    assert closed.value.code == "BUSINESS.CLOSED"

    with pytest.raises(ForbiddenError) as frozen:
        assert_business_allows_create(_Business(BusinessStatus.FROZEN))
    assert frozen.value.code == "BUSINESS.FROZEN"


def test_assert_business_not_closed():
    assert_business_not_closed(_Business(BusinessStatus.ACTIVE))

    with pytest.raises(ForbiddenError) as exc:
        assert_business_not_closed(_Business(BusinessStatus.CLOSED))
    assert exc.value.code == "BUSINESS.CLOSED"


def test_validate_business_for_create_returns_business(monkeypatch, test_db):
    expected = SimpleNamespace(id=123, status=BusinessStatus.ACTIVE)
    monkeypatch.setattr(
        "app.businesses.services.business_guards.get_business_or_raise",
        lambda db, business_id: expected,
    )
    business = validate_business_for_create(test_db, expected.id)
    assert business.id == expected.id


def test_validate_business_for_create_raises_not_found(test_db):
    with pytest.raises(NotFoundError) as exc:
        validate_business_for_create(test_db, 999999)
    assert exc.value.code == "BUSINESS.NOT_FOUND"


def test_validate_business_for_create_blocks_frozen(monkeypatch, test_db):
    monkeypatch.setattr(
        "app.businesses.services.business_guards.get_business_or_raise",
        lambda db, business_id: SimpleNamespace(status=BusinessStatus.FROZEN),
    )

    with pytest.raises(ForbiddenError) as exc:
        validate_business_for_create(test_db, 1)
    assert exc.value.code == "BUSINESS.FROZEN"
