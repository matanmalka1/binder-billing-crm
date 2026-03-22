import pytest

from app.businesses.models.business import BusinessStatus
from app.businesses.services.business_guards import assert_business_allows_create, assert_business_not_closed
from app.core.exceptions import ForbiddenError


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
