from datetime import date
from types import SimpleNamespace

import pytest

from app.businesses.services.business_bulk_service import BusinessBulkService
from app.core.exceptions import AppError


def test_list_businesses_without_has_signals_delegates_to_repo(test_db):
    service = BusinessBulkService(test_db)
    expected_items = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    service.business_repo = SimpleNamespace(
        list=lambda **kwargs: expected_items,
        count=lambda **kwargs: 2,
    )

    items, total = service.list_businesses(
        status="active",
        business_type="company",
        search="Acme",
        has_signals=None,
        page=2,
        page_size=5,
    )

    assert items == expected_items
    assert total == 2


def test_list_businesses_with_has_signals_filters_and_paginates(test_db):
    service = BusinessBulkService(test_db)
    businesses = [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)]
    service.business_repo = SimpleNamespace(
        count=lambda **kwargs: 3,
        list=lambda **kwargs: businesses,
    )
    service._has_signals = lambda business_id, _reference_date: business_id in {1, 3}

    items, total = service.list_businesses(
        has_signals=True,
        page=2,
        page_size=1,
        reference_date=date(2026, 1, 1),
    )

    assert total == 2
    assert [b.id for b in items] == [3]


def test_check_signal_limit_raises_when_exceeding_limit(test_db):
    service = BusinessBulkService(test_db)

    with pytest.raises(AppError) as exc:
        service.check_signal_limit(1001)

    assert exc.value.code == "BUSINESS.SIGNAL_FILTER_LIMIT"


def test_bulk_update_status_is_not_exposed(test_db):
    service = BusinessBulkService(test_db)
    assert hasattr(service, "list_businesses")
    assert not hasattr(service, "bulk_update_status")
