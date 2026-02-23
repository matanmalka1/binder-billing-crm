from unittest.mock import MagicMock

import pytest

from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.services import intake
from tests.services.vat_report_test_utils import make_item


class TestCreateWorkItem:
    def test_happy_path_material_received(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()

        client_repo.get_by_id.return_value = MagicMock()
        work_item_repo.get_by_client_period.return_value = None
        work_item_repo.create.return_value = make_item()

        result = intake.create_work_item(
            work_item_repo,
            client_repo,
            client_id=10,
            period="2026-01",
            created_by=1,
        )

        work_item_repo.create.assert_called_once()
        work_item_repo.append_audit.assert_called_once()
        assert result.status == VatWorkItemStatus.MATERIAL_RECEIVED

    def test_client_not_found_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            intake.create_work_item(
                work_item_repo, client_repo, client_id=99, period="2026-01", created_by=1
            )

    def test_duplicate_period_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = MagicMock()
        work_item_repo.get_by_client_period.return_value = make_item()

        with pytest.raises(ValueError, match="already exists"):
            intake.create_work_item(
                work_item_repo, client_repo, client_id=10, period="2026-01", created_by=1
            )

    def test_pending_without_note_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = MagicMock()
        work_item_repo.get_by_client_period.return_value = None

        with pytest.raises(ValueError, match="pending_materials_note"):
            intake.create_work_item(
                work_item_repo,
                client_repo,
                client_id=10,
                period="2026-01",
                created_by=1,
                mark_pending=True,
            )

    def test_pending_with_note_creates_item(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.get_by_id.return_value = MagicMock()
        work_item_repo.get_by_client_period.return_value = None
        pending_item = make_item(status=VatWorkItemStatus.PENDING_MATERIALS)
        work_item_repo.create.return_value = pending_item

        result = intake.create_work_item(
            work_item_repo,
            client_repo,
            client_id=10,
            period="2026-01",
            created_by=1,
            mark_pending=True,
            pending_materials_note="Missing Q4 invoices",
        )
        assert result.status == VatWorkItemStatus.PENDING_MATERIALS


class TestMarkMaterialsComplete:
    def test_happy_path(self):
        work_item_repo = MagicMock()
        item = make_item(status=VatWorkItemStatus.PENDING_MATERIALS)
        work_item_repo.get_by_id.return_value = item
        work_item_repo.update_status.return_value = make_item(
            status=VatWorkItemStatus.MATERIAL_RECEIVED
        )

        result = intake.mark_materials_complete(work_item_repo, item_id=1, performed_by=1)
        assert result.status == VatWorkItemStatus.MATERIAL_RECEIVED

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id.return_value = make_item(
            status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        )

        with pytest.raises(ValueError, match="Cannot mark materials complete"):
            intake.mark_materials_complete(work_item_repo, item_id=1, performed_by=1)
