from unittest.mock import MagicMock

import pytest

from app.annual_reports.models.annual_report_enums import SubmissionMethod
from app.core.exceptions import AppError, NotFoundError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.services import data_entry, filing
from tests.vat_reports.service.test_vat_report_test_utils import make_item


class TestMarkReadyForReview:
    def test_happy_path(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)
        work_item_repo.update_status.return_value = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW)

        result = data_entry.mark_ready_for_review(work_item_repo, item_id=1, performed_by=1)
        assert result.status == VatWorkItemStatus.READY_FOR_REVIEW

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.MATERIAL_RECEIVED)

        with pytest.raises(AppError) as exc_info:
            data_entry.mark_ready_for_review(work_item_repo, item_id=1, performed_by=1)
        assert exc_info.value.code == "VAT.INVALID_TRANSITION"


class TestSendBackForCorrection:
    def test_happy_path(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW)
        work_item_repo.update_status.return_value = make_item(status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

        result = data_entry.send_back_for_correction(
            work_item_repo,
            item_id=1,
            performed_by=1,
            correction_note="Invoice #5 is missing counterparty ID",
        )
        assert result.status == VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        work_item_repo.append_audit.assert_called_once()

    def test_empty_note_raises(self):
        work_item_repo = MagicMock()

        with pytest.raises(AppError) as exc_info:
            data_entry.send_back_for_correction(
                work_item_repo, item_id=1, performed_by=1, correction_note="   "
            )
        assert exc_info.value.code == "VAT.JUSTIFICATION_REQUIRED"


class TestFileVatReturn:
    def test_happy_path_system_calculated(self):
        work_item_repo = MagicMock()
        item = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW, net_vat=500.0)
        work_item_repo.get_by_id.return_value = item
        work_item_repo.mark_filed.return_value = make_item(status=VatWorkItemStatus.FILED)

        result = filing.file_vat_return(
            work_item_repo,
            item_id=1,
            filed_by=2,
            submission_method=SubmissionMethod.ONLINE,
        )

        work_item_repo.mark_filed.assert_called_once_with(
            item_id=1,
            final_vat_amount=500.0,
            submission_method=SubmissionMethod.ONLINE,
            filed_by=2,
            is_overridden=False,
            override_justification=None,
            submission_reference=None,
            is_amendment=False,
            amends_item_id=None,
        )
        assert result.status == VatWorkItemStatus.FILED

    def test_override_with_justification_logged(self):
        work_item_repo = MagicMock()
        item = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW, net_vat=300.0)
        work_item_repo.get_by_id.return_value = item
        work_item_repo.mark_filed.return_value = make_item(status=VatWorkItemStatus.FILED)

        filing.file_vat_return(
            work_item_repo,
            item_id=1,
            filed_by=2,
            submission_method=SubmissionMethod.MANUAL,
            override_amount=400.0,
            override_justification="Client provided corrected invoice post-review",
        )

        work_item_repo.mark_filed.assert_called_once_with(
            item_id=1,
            final_vat_amount=400.0,
            submission_method=SubmissionMethod.MANUAL,
            filed_by=2,
            is_overridden=True,
            override_justification="Client provided corrected invoice post-review",
            submission_reference=None,
            is_amendment=False,
            amends_item_id=None,
        )
        assert work_item_repo.append_audit.call_count == 2

    def test_override_without_justification_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW)

        with pytest.raises(AppError) as exc_info:
            filing.file_vat_return(
                work_item_repo,
                item_id=1,
                filed_by=2,
                submission_method=SubmissionMethod.MANUAL,
                override_amount=1000.0,
                override_justification=None,
            )
        assert exc_info.value.code == "VAT.JUSTIFICATION_REQUIRED"

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

        with pytest.raises(AppError) as exc_info:
            filing.file_vat_return(
                work_item_repo,
                item_id=1,
                filed_by=2,
                submission_method=SubmissionMethod.ONLINE,
            )
        assert exc_info.value.code == "VAT.INVALID_TRANSITION"

    def test_not_found_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            filing.file_vat_return(
                work_item_repo, item_id=999, filed_by=2, submission_method=SubmissionMethod.ONLINE
            )
        assert exc_info.value.code == "VAT.NOT_FOUND"
