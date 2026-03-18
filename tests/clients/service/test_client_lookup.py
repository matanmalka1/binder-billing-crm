import pytest

from app.clients.models.client import ClientStatus
from app.clients.services.client_lookup import (
    assert_client_allows_create,
    assert_client_not_closed,
)
from app.core.exceptions import ForbiddenError


def test_assert_client_allows_create_blocks_closed_and_frozen():
    closed = type("C", (), {"status": ClientStatus.CLOSED})()
    frozen = type("C", (), {"status": ClientStatus.FROZEN})()

    with pytest.raises(ForbiddenError) as closed_exc:
        assert_client_allows_create(closed)
    assert closed_exc.value.code == "CLIENT.CLOSED"

    with pytest.raises(ForbiddenError) as frozen_exc:
        assert_client_allows_create(frozen)
    assert frozen_exc.value.code == "CLIENT.FROZEN"


def test_assert_client_not_closed_only_blocks_closed():
    active = type("C", (), {"status": ClientStatus.ACTIVE})()
    frozen = type("C", (), {"status": ClientStatus.FROZEN})()
    closed = type("C", (), {"status": ClientStatus.CLOSED})()

    assert_client_not_closed(active)
    assert_client_not_closed(frozen)

    with pytest.raises(ForbiddenError) as exc:
        assert_client_not_closed(closed)
    assert exc.value.code == "CLIENT.CLOSED"

