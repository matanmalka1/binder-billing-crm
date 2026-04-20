from unittest.mock import MagicMock

import pytest

from app.common.enums import EntityType
from app.common.enums import VatType
from app.clients.models.client import ClientStatus
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.services import intake
from tests.vat_reports.service.test_vat_report_test_utils import make_item


def _mock_osek_murshe_business(client_id=1):
    """Return a mock OSEK_MURSHE business whose client has no vat_reporting_frequency set (defaults to BIMONTHLY)."""
    return MagicMock(entity_type=EntityType.OSEK_MURSHE, client_id=client_id)


class TestCreateWorkItem:
    def test_happy_path_material_received(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_record = MagicMock(id=1, status=ClientStatus.ACTIVE)

        client_repo.db = MagicMock()
        client_repo.get_by_id.return_value = MagicMock(vat_reporting_frequency=None)
        work_item_repo.get_by_client_record_period.return_value = None
        work_item_repo.create.return_value = make_item()

        from app.clients.repositories.client_record_repository import ClientRecordRepository
        ClientRecordRepository(client_repo.db).get_by_client_id = MagicMock(return_value=client_record)

        result = intake.create_work_item(work_item_repo, client_repo, client_id=10, period="2026-01", created_by=1)

        work_item_repo.create.assert_called_once()
        work_item_repo.append_audit.assert_called_once()
        assert result.status == VatWorkItemStatus.MATERIAL_RECEIVED

    def test_client_not_found_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.db = MagicMock()
        client_repo.get_by_id.return_value = None
        from app.clients.repositories.client_record_repository import ClientRecordRepository
        ClientRecordRepository(client_repo.db).get_by_client_id = MagicMock(return_value=MagicMock(id=99, status=ClientStatus.ACTIVE))

        with pytest.raises(NotFoundError) as exc_info:
            intake.create_work_item(work_item_repo, client_repo, client_id=99, period="2026-01", created_by=1)
        assert exc_info.value.code == "VAT.NOT_FOUND"

    def test_duplicate_period_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.db = MagicMock()
        client_repo.get_by_id.return_value = MagicMock(vat_reporting_frequency=None)
        work_item_repo.get_by_client_record_period.return_value = make_item()
        from app.clients.repositories.client_record_repository import ClientRecordRepository
        ClientRecordRepository(client_repo.db).get_by_client_id = MagicMock(return_value=MagicMock(id=10, status=ClientStatus.ACTIVE))

        with pytest.raises(ConflictError) as exc_info:
            intake.create_work_item(work_item_repo, client_repo, client_id=10, period="2026-01", created_by=1)
        assert exc_info.value.code == "VAT.CONFLICT"

    def test_pending_without_note_raises(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.db = MagicMock()
        client_repo.get_by_id.return_value = MagicMock(vat_reporting_frequency=None)
        work_item_repo.get_by_client_record_period.return_value = None
        from app.clients.repositories.client_record_repository import ClientRecordRepository
        ClientRecordRepository(client_repo.db).get_by_client_id = MagicMock(return_value=MagicMock(id=10, status=ClientStatus.ACTIVE))

        with pytest.raises(AppError) as exc_info:
            intake.create_work_item(
                work_item_repo,
                client_repo,
                client_id=10,
                period="2026-01",
                created_by=1,
                mark_pending=True,
            )
        assert exc_info.value.code == "VAT.PENDING_NOTE_REQUIRED"

    def test_pending_with_note_creates_item(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.db = MagicMock()
        client_repo.get_by_id.return_value = MagicMock(vat_reporting_frequency=None)
        work_item_repo.get_by_client_record_period.return_value = None
        pending_item = make_item(status=VatWorkItemStatus.PENDING_MATERIALS)
        work_item_repo.create.return_value = pending_item
        from app.clients.repositories.client_record_repository import ClientRecordRepository
        ClientRecordRepository(client_repo.db).get_by_client_id = MagicMock(return_value=MagicMock(id=10, status=ClientStatus.ACTIVE))

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

    def test_exempt_vat_type_rejected(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.db = MagicMock()
        client_repo.get_by_id.return_value = MagicMock(vat_reporting_frequency=VatType.EXEMPT, status=ClientStatus.ACTIVE)
        work_item_repo.get_by_client_record_period.return_value = None
        from app.clients.repositories.client_record_repository import ClientRecordRepository
        ClientRecordRepository(client_repo.db).get_by_client_id = MagicMock(return_value=MagicMock(id=10, status=ClientStatus.ACTIVE))

        with pytest.raises(AppError) as exc_info:
            intake.create_work_item(work_item_repo, client_repo, client_id=10, period="2026-01", created_by=1)
        assert exc_info.value.code == "VAT.CLIENT_EXEMPT"

    def test_bimonthly_rejects_even_month(self):
        work_item_repo = MagicMock()
        client_repo = MagicMock()
        client_repo.db = MagicMock()
        client_repo.get_by_id.return_value = MagicMock(vat_reporting_frequency=VatType.BIMONTHLY, status=ClientStatus.ACTIVE)
        work_item_repo.get_by_client_record_period.return_value = None
        from app.clients.repositories.client_record_repository import ClientRecordRepository
        ClientRecordRepository(client_repo.db).get_by_client_id = MagicMock(return_value=MagicMock(id=10, status=ClientStatus.ACTIVE))

        with pytest.raises(AppError) as exc_info:
            intake.create_work_item(work_item_repo, client_repo, client_id=10, period="2026-02", created_by=1)
        assert exc_info.value.code == "VAT.INVALID_PERIOD_FOR_FREQUENCY"


class TestMarkMaterialsComplete:
    def test_happy_path(self):
        work_item_repo = MagicMock()
        item = make_item(status=VatWorkItemStatus.PENDING_MATERIALS)
        work_item_repo.get_by_id_for_update.return_value = item
        work_item_repo.update_status.return_value = make_item(
            status=VatWorkItemStatus.MATERIAL_RECEIVED
        )

        result = intake.mark_materials_complete(work_item_repo, item_id=1, performed_by=1)
        assert result.status == VatWorkItemStatus.MATERIAL_RECEIVED

    def test_wrong_status_raises(self):
        work_item_repo = MagicMock()
        work_item_repo.get_by_id_for_update.return_value = make_item(
            status=VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS
        )

        with pytest.raises(AppError) as exc_info:
            intake.mark_materials_complete(work_item_repo, item_id=1, performed_by=1)
        assert exc_info.value.code == "VAT.INVALID_TRANSITION"
