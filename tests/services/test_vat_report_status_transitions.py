from unittest.mock import MagicMock

import pytest

from app.vat_reports.models.vat_enums import FilingMethod, VatWorkItemStatus
from app.vat_reports.services import data_entry, filing
from tests.services.vat_report_test_utils import make_item


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

        with pytest.raises(ValueError, match="Cannot mark ready for review"):
            data_entry.mark_ready_for_review(work_item_repo, item_id=1, performed_by=1)


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

        with pytest.raises(ValueError, match="correction_note"):
            data_entry.send_back_for_correction(
                work_item_repo, item_id=1, performed_by=1, correction_note="   "
            )


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
            filing_method=FilingMethod.ONLINE,
        )

        work_item_repo.mark_filed.assert_called_once_with(
            item_id=1,
            final_vat_amount=500.0,
            filing_method=FilingMethod.ONLINE,
            filed_by=2,
            is_overridden=False,
            override_justification=None,
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
            filing_method=FilingMethod.MANUAL,
            override_amount=400.0,
            override_justification="Client provided corrected invoice post-review",
        )

        work_item_repo.mark_filed.assert_called_once_with(
            item_id=1,
            final_vat_amount=400.0,
            filing_method=FilingMethod.MANUAL,
            filed_by=2,
            is_overridden=True,
            override_justification="Client provided corrected invoice post-review",
        )
        assert work_item_repo.append_audit.call_count == 2

    def test_override_without_justification_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.READY_FOR_REVIEW)

        with pytest.raises(ValueError, match="justification"):
            filing.file_vat_return(
                work_item_repo,
                item_id=1,
                filed_by=2,
                filing_method=FilingMethod.MANUAL,
                override_amount=1000.0,
                override_justification=None,
            )

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS)

        with pytest.raises(ValueError, match="READY_FOR_REVIEW"):
            filing.file_vat_return(
                work_item_repo,
                item_id=1,
                filed_by=2,
                filing_method=FilingMethod.ONLINE,
            )

    def test_not_found_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            filing.file_vat_return(work_item_repo, item_id=999, filed_by=2, filing_method=FilingMethod.ONLINE)
