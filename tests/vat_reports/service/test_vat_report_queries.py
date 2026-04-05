from unittest.mock import MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.services import vat_report_queries
from tests.vat_reports.service.test_vat_report_test_utils import make_item


def test_get_work_item_not_found_raises_not_found_error():
    work_item_repo = MagicMock()
    work_item_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError) as exc_info:
        vat_report_queries.get_work_item(work_item_repo, item_id=999)

    assert exc_info.value.code == "VAT.NOT_FOUND"


def test_list_business_work_items_forwards_repository_call():
    work_item_repo = MagicMock()
    expected = [make_item(id=1), make_item(id=2)]
    work_item_repo.list_by_business.return_value = expected

    result = vat_report_queries.list_business_work_items(work_item_repo, business_id=11)

    work_item_repo.list_by_business.assert_called_once_with(11)
    assert result == expected


def test_list_work_items_by_status_short_circuits_when_business_search_empty():
    work_item_repo = MagicMock()
    business_repo = MagicMock()
    business_repo.list.return_value = []

    items, total = vat_report_queries.list_work_items_by_status(
        work_item_repo=work_item_repo,
        business_repo=business_repo,
        status=VatWorkItemStatus.MATERIAL_RECEIVED,
        business_name="no match",
    )

    assert items == []
    assert total == 0
    work_item_repo.list_by_status.assert_not_called()
    work_item_repo.count_by_status.assert_not_called()


def test_list_work_items_by_status_uses_resolved_business_ids():
    work_item_repo = MagicMock()
    business_repo = MagicMock()
    business_repo.list.return_value = [MagicMock(id=7), MagicMock(id=8)]
    work_item_repo.list_by_status.return_value = [make_item(id=1)]
    work_item_repo.count_by_status.return_value = 1

    items, total = vat_report_queries.list_work_items_by_status(
        work_item_repo=work_item_repo,
        business_repo=business_repo,
        status=VatWorkItemStatus.PENDING_MATERIALS,
        business_name="Business",
        period="2026-01",
        page=2,
        page_size=25,
    )

    assert len(items) == 1
    assert total == 1
    work_item_repo.list_by_status.assert_called_once_with(
        VatWorkItemStatus.PENDING_MATERIALS,
        page=2,
        page_size=25,
        period="2026-01",
        business_ids=[7, 8],
    )
    work_item_repo.count_by_status.assert_called_once_with(
        VatWorkItemStatus.PENDING_MATERIALS,
        period="2026-01",
        business_ids=[7, 8],
    )


def test_list_all_work_items_without_name_filter_passes_none_business_ids():
    work_item_repo = MagicMock()
    business_repo = MagicMock()
    work_item_repo.list_all.return_value = [make_item(id=3)]
    work_item_repo.count_all.return_value = 1

    items, total = vat_report_queries.list_all_work_items(
        work_item_repo=work_item_repo,
        business_repo=business_repo,
        page=1,
        page_size=10,
        period="2026-02",
    )

    assert len(items) == 1
    assert total == 1
    business_repo.list.assert_not_called()
    work_item_repo.list_all.assert_called_once_with(
        page=1, page_size=10, period="2026-02", business_ids=None
    )
    work_item_repo.count_all.assert_called_once_with(
        period="2026-02", business_ids=None
    )


def test_list_invoices_forwards_invoice_type():
    invoice_repo = MagicMock()
    invoice_repo.list_by_work_item.return_value = ["i1"]

    result = vat_report_queries.list_invoices(
        invoice_repo=invoice_repo,
        item_id=5,
        invoice_type=InvoiceType.EXPENSE,
    )

    assert result == ["i1"]
    invoice_repo.list_by_work_item.assert_called_once_with(
        5, invoice_type=InvoiceType.EXPENSE
    )


def test_get_audit_trail_forwards_call():
    work_item_repo = MagicMock()
    work_item_repo.get_audit_trail.return_value = ["a1", "a2"]

    result = vat_report_queries.get_audit_trail(work_item_repo, item_id=12)

    assert result == ["a1", "a2"]
    work_item_repo.get_audit_trail.assert_called_once_with(12)


def test_compute_deadline_fields_rolls_december_to_next_year():
    item = MagicMock()
    item.period = "2030-12"

    result = vat_report_queries.compute_deadline_fields(item)

    assert str(result["submission_deadline"]) == "2031-01-15"
    assert str(result["statutory_deadline"]) == "2031-01-15"
    assert str(result["extended_deadline"]) == "2031-01-19"
    assert isinstance(result["days_until_deadline"], int)
    assert isinstance(result["is_overdue"], bool)


def test_compute_deadline_fields_invalid_period_returns_nones(caplog):
    item = MagicMock()
    item.period = "bad-period"

    with caplog.at_level("WARNING"):
        result = vat_report_queries.compute_deadline_fields(item)

    assert result == {
        "submission_deadline": None,
        "statutory_deadline": None,
        "extended_deadline": None,
        "days_until_deadline": None,
        "is_overdue": None,
    }
    assert "Failed to compute deadline for period 'bad-period'" in caplog.text
