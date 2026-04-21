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
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.clients.repositories.person_repository import PersonRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_record_read_repository import get_full_record
from app.core.exceptions import ForbiddenError, NotFoundError
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.users.models.user import UserRole
from app.vat_reports.repositories.vat_work_item_write_repository import VatWorkItemWriteRepository

_log = logging.getLogger(__name__)


class ClientUpdateService:
    def __init__(self, db: Session):
        self.db = db
        self.record_repo = ClientRecordRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def update_client(self, client_id: int, actor_id: Optional[int] = None, actor_role=None, **fields):
        existing = get_full_record(self.db, client_id)
        if not existing:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        new_status = fields.get("status")
        new_entity_type = fields.get("entity_type")
        old_entity_type = existing.get("entity_type")
        if new_entity_type is not None and new_entity_type != old_entity_type:
            if actor_role != UserRole.ADVISOR:
                raise ForbiddenError("שינוי סוג ישות מותר לרואה חשבון בלבד", "CLIENT.ENTITY_TYPE_CHANGE_FORBIDDEN")
            self._cancel_deadlines_on_entity_type_change(client_id, old_entity_type, new_entity_type, actor_id)
        old_snapshot = {k: existing.get(k) for k in fields if k in existing}
        updated = self._update_client_record_graph(client_id, **fields)
        if new_status is not None:
            self._update_client_record_status(client_id, new_status)
        if obligation_fields_changed(fields):
            generate_client_obligations(
                self.db, client_id, actor_id=actor_id,
                entity_type=updated.get("entity_type"),
                best_effort=True,
            )
        self._audit.append(
            entity_type=ENTITY_CLIENT,
            entity_id=client_id,
            performed_by=actor_id,
            action=ACTION_UPDATED,
            old_value=json.dumps({k: str(v) if v is not None else None for k, v in old_snapshot.items()}),
            new_value=json.dumps(
                {
                    k: str(updated.get(k)) if updated.get(k) is not None else None
                    for k in fields
                }
            ),
        )
        return updated

    def _update_client_record_graph(self, client_id: int, **fields):
        record = self.record_repo.get_by_id(client_id)
        legal_entity = LegalEntityRepository(self.db).get_by_id(record.legal_entity_id) if record else None
        if not record or not legal_entity:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        person = PersonRepository(self.db).get_owner_for_legal_entity(legal_entity.id)
        person_fields = {
            "phone",
            "email",
            "address_street",
            "address_building_number",
            "address_apartment",
            "address_city",
            "address_zip_code",
        }
        legal_entity_fields = {
            "entity_type",
            "vat_reporting_frequency",
            "vat_exempt_ceiling",
            "advance_rate",
            "advance_rate_updated_at",
        }
        record_fields = {"status", "accountant_name", "notes"}
        if "full_name" in fields:
            legal_entity.official_name = fields["full_name"]
            if person is not None:
                person.full_name = fields["full_name"]
        for key, value in fields.items():
            if key in person_fields and person is not None:
                setattr(person, key, value)
            elif key in legal_entity_fields:
                setattr(legal_entity, key, value)
            elif key in record_fields:
                setattr(record, key, value)
        self.db.flush()
        updated = get_full_record(self.db, client_id)
        if not updated:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        return updated

    def _update_client_record_status(self, client_id: int, new_status: ClientStatus) -> None:
        record = self.record_repo.get_by_id(client_id)
        if not record:
            return
        self.record_repo.update_status(record.id, new_status)
        if new_status in {ClientStatus.CLOSED, ClientStatus.FROZEN}:
            ReminderRepository(self.db).cancel_pending_by_client_record(record.id)
            TaxDeadlineRepository(self.db).cancel_pending_by_client_record(record.id)
            VatWorkItemWriteRepository(self.db).cancel_open_by_client_record(record.id)
            AnnualReportReportRepository(self.db).cancel_open_by_client_record(record.id)
            BinderRepository(self.db).archive_in_office_by_client_record(record.id)

    def _cancel_deadlines_on_entity_type_change(self, client_id: int, old_entity_type, new_entity_type, actor_id):
        record = self.record_repo.get_by_id(client_id)
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
