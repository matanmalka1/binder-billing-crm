"""
Tests verifying that VAT work item transition functions use the locked fetch
path (get_by_id_for_update) and correctly enforce state guards.

All service functions accept a repo object, so we use MagicMock repos — this
matches the existing pattern in the vat_reports service test suite.

Note: SQLite does not support real SELECT … FOR UPDATE blocking.
Tests verify code path (monkeypatch spy on mock) and invalid-state handling.
"""
from unittest.mock import MagicMock, call

import pytest

from app.common.enums import SubmissionMethod
from app.core.exceptions import AppError, NotFoundError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.services import data_entry_status, filing, intake
from tests.vat_reports.service.test_vat_report_test_utils import make_item


# ── mark_materials_complete ───────────────────────────────────────────────────

def test_mark_materials_complete_uses_locked_fetch():
    item = make_item(status=VatWorkItemStatus.PENDING_MATERIALS)
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = item
    repo.update_status.return_value = make_item(status=VatWorkItemStatus.MATERIAL_RECEIVED)

    intake.mark_materials_complete(repo, item_id=1, performed_by=1)

    repo.get_by_id_for_update.assert_called_once_with(1)
    repo.get_by_id.assert_not_called()


def test_mark_materials_complete_wrong_status_raises():
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = make_item(status=VatWorkItemStatus.MATERIAL_RECEIVED)

    with pytest.raises(AppError) as exc:
        intake.mark_materials_complete(repo, item_id=1, performed_by=1)
    assert exc.value.code == "VAT.INVALID_TRANSITION"


# ── mark_ready_for_review ─────────────────────────────────────────────────────

def test_mark_ready_for_review_uses_locked_fetch():
    item = make_item(status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = item
    repo.update_status.return_value = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW)

    data_entry_status.mark_ready_for_review(repo, item_id=1, performed_by=1)

    repo.get_by_id_for_update.assert_called_once_with(1)
    repo.get_by_id.assert_not_called()


def test_mark_ready_for_review_wrong_status_raises():
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW)

    with pytest.raises(AppError) as exc:
        data_entry_status.mark_ready_for_review(repo, item_id=1, performed_by=1)
    assert exc.value.code == "VAT.INVALID_TRANSITION"


# ── send_back_for_correction ──────────────────────────────────────────────────

def test_send_back_for_correction_uses_locked_fetch():
    item = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW)
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = item
    repo.update_status.return_value = make_item(status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

    data_entry_status.send_back_for_correction(repo, item_id=1, performed_by=1, correction_note="fix this")

    repo.get_by_id_for_update.assert_called_once_with(1)
    repo.get_by_id.assert_not_called()


def test_send_back_for_correction_wrong_status_raises():
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = make_item(status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

    with pytest.raises(AppError) as exc:
        data_entry_status.send_back_for_correction(repo, item_id=1, performed_by=1, correction_note="fix")
    assert exc.value.code == "VAT.INVALID_TRANSITION"


# ── file_vat_return ───────────────────────────────────────────────────────────

def test_file_vat_return_uses_locked_fetch():
    item = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW, net_vat=500.0)
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = item
    repo.mark_filed.return_value = make_item(status=VatWorkItemStatus.FILED)

    filing.file_vat_return(
        repo,
        item_id=1,
        filed_by=1,
        submission_method=SubmissionMethod.ONLINE,
    )

    repo.get_by_id_for_update.assert_called_once_with(1)
    repo.get_by_id.assert_not_called()


def test_file_vat_return_already_filed_raises():
    repo = MagicMock()
    repo.get_by_id_for_update.return_value = make_item(status=VatWorkItemStatus.FILED)

    with pytest.raises(AppError) as exc:
        filing.file_vat_return(
            repo,
            item_id=1,
            filed_by=1,
            submission_method=SubmissionMethod.ONLINE,
        )
    assert exc.value.code == "VAT.INVALID_TRANSITION"
