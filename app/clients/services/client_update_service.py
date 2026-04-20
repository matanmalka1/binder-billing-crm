import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.actions.obligation_orchestrator import generate_client_obligations, obligation_fields_changed
from app.audit.constants import ACTION_UPDATED, ENTITY_CLIENT
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.enums import ClientStatus
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import ForbiddenError, NotFoundError
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.users.models.user import UserRole
from app.vat_reports.repositories.vat_work_item_write_repository import VatWorkItemWriteRepository

_log = logging.getLogger(__name__)


class ClientUpdateService:
    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def update_client(self, client_id: int, actor_id: Optional[int] = None, actor_role=None, **fields):
        existing = self.client_repo.get_by_id(client_id)
        if not existing:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        new_status = fields.get("status")
        new_entity_type = fields.get("entity_type")
        old_entity_type = existing.entity_type
        if new_entity_type is not None and new_entity_type != old_entity_type:
            if actor_role != UserRole.ADVISOR:
                raise ForbiddenError("שינוי סוג ישות מותר לרואה חשבון בלבד", "CLIENT.ENTITY_TYPE_CHANGE_FORBIDDEN")
            self._cancel_deadlines_on_entity_type_change(client_id, old_entity_type, new_entity_type, actor_id)
        old_snapshot = {k: getattr(existing, k, None) for k in fields if hasattr(existing, k)}
        updated = self.client_repo.update(client_id, **fields)
        if new_status is not None:
            self._update_client_record_status(client_id, new_status)
        if obligation_fields_changed(fields):
            generate_client_obligations(
                self.db, client_id, actor_id=actor_id,
                entity_type=getattr(updated, "entity_type", None),
                best_effort=True,
            )
        self._audit.append(
            entity_type=ENTITY_CLIENT,
            entity_id=client_id,
            performed_by=actor_id,
            action=ACTION_UPDATED,
            old_value=json.dumps({k: str(v) if v is not None else None for k, v in old_snapshot.items()}),
            new_value=json.dumps({k: str(getattr(updated, k, None)) if getattr(updated, k, None) is not None else None for k in fields}),
        )
        return updated

    def _update_client_record_status(self, client_id: int, new_status: ClientStatus) -> None:
        record = ClientRecordRepository(self.db).get_by_id(client_id)
        if not record:
            return
        ClientRecordRepository(self.db).update_status(record.id, new_status)
        if new_status in {ClientStatus.CLOSED, ClientStatus.FROZEN}:
            ReminderRepository(self.db).cancel_pending_by_client_record(record.id)
            TaxDeadlineRepository(self.db).cancel_pending_by_client_record(record.id)
            VatWorkItemWriteRepository(self.db).cancel_open_by_client_record(record.id)
            AnnualReportReportRepository(self.db).cancel_open_by_client_record(record.id)
            BinderRepository(self.db).archive_in_office_by_client_record(record.id)

    def _cancel_deadlines_on_entity_type_change(self, client_id: int, old_entity_type, new_entity_type, actor_id):
        record = ClientRecordRepository(self.db).get_by_id(client_id)
        if not record:
            return
        canceled = TaxDeadlineRepository(self.db).cancel_pending_by_client_record(record.id)
        _log.warning(
            "entity_type_changed: client_id=%s old=%s new=%s canceled_deadlines=%s actor=%s",
            client_id, old_entity_type, new_entity_type, canceled, actor_id,
        )
        self._audit.append(
            entity_type=ENTITY_CLIENT,
            entity_id=client_id,
            performed_by=actor_id,
            action="entity_type_changed",
            old_value=str(old_entity_type),
            new_value=str(new_entity_type),
        )
