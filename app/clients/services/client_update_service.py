import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.actions.obligation_orchestrator import (
    generate_client_obligations,
    obligation_fields_changed,
)
from app.audit.constants import ACTION_ENTITY_TYPE_CHANGED, ENTITY_CLIENT
from app.audit.services.entity_audit_writer import EntityAuditWriter
from app.annual_reports.services.client_status_service import (
    AnnualReportClientStatusService,
)
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.enums import ClientStatus
from app.clients.repositories.client_record_read_repository import (
    get_full_record,
)
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import ForbiddenError, NotFoundError
from app.users.models.user import UserRole
from app.vat_reports.services.client_status_service import (
    VatWorkItemClientStatusService,
)

_log = logging.getLogger(__name__)

_PERSON_FIELDS = frozenset(
    {
        "phone",
        "email",
        "address_street",
        "address_building_number",
        "address_apartment",
        "address_city",
        "address_zip_code",
    }
)
_LEGAL_ENTITY_FIELDS = frozenset(
    {
        "entity_type",
        "vat_reporting_frequency",
        "advance_payment_frequency",
        "advance_rate",
        "advance_rate_updated_at",
        "annual_revenue",
    }
)
_RECORD_FIELDS = frozenset({"status", "accountant_id"})


def apply_graph_update(db, client_id: int, **fields) -> dict:
    """Apply **fields to the Person / LegalEntity / ClientRecord graph and flush.

    Returns the refreshed full-record dict, or raises NotFoundError.
    """
    from app.clients.repositories.legal_entity_repository import LegalEntityRepository
    from app.clients.repositories.person_repository import PersonRepository
    from app.core.exceptions import NotFoundError

    repo = ClientRecordRepository(db)
    record = repo.get_by_id(client_id)
    legal_entity = (
        LegalEntityRepository(db).get_by_id(record.legal_entity_id) if record else None
    )
    if not record or not legal_entity:
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
    person = PersonRepository(db).get_owner_for_legal_entity(legal_entity.id)
    if "full_name" in fields:
        legal_entity.official_name = fields["full_name"]
        if person is not None:
            person.full_name = fields["full_name"]
    for key, value in fields.items():
        if key in _PERSON_FIELDS and person is not None:
            setattr(person, key, value)
        elif key in _LEGAL_ENTITY_FIELDS:
            setattr(legal_entity, key, value)
        elif key in _RECORD_FIELDS:
            setattr(record, key, value)
    db.flush()
    updated = get_full_record(db, client_id)
    if not updated:
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
    return updated


class ClientUpdateService:
    def __init__(self, db: Session):
        self.db = db
        self.record_repo = ClientRecordRepository(db)
        self._audit = EntityAuditWriter(db)

    def update_client(
        self, client_id: int, actor_id: Optional[int] = None, actor_role=None, **fields
    ):
        existing = get_full_record(self.db, client_id)
        if not existing:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        new_status = fields.get("status")
        new_entity_type = fields.get("entity_type")
        old_entity_type = existing.get("entity_type")
        if new_entity_type is not None and new_entity_type != old_entity_type:
            if actor_role != UserRole.ADVISOR:
                raise ForbiddenError(
                    "שינוי סוג ישות מותר לרואה חשבון בלבד",
                    "CLIENT.ENTITY_TYPE_CHANGE_FORBIDDEN",
                )
            self._cancel_deadlines_on_entity_type_change(
                client_id, old_entity_type, new_entity_type, actor_id
            )
        old_snapshot = {k: existing.get(k) for k in fields if k in existing}
        updated = self._update_client_record_graph(client_id, **fields)
        if new_status is not None:
            self._update_client_record_status(client_id, new_status)
        if obligation_fields_changed(fields):
            generate_client_obligations(
                self.db,
                client_id,
                actor_id=actor_id,
                entity_type=updated.get("entity_type"),
                best_effort=True,
            )
        self._audit.record_update(
            ENTITY_CLIENT,
            client_id,
            actor_id,
            old_value=old_snapshot,
            new_value={k: updated.get(k) for k in fields},
        )
        return updated

    def _update_client_record_graph(self, client_id: int, **fields):
        return apply_graph_update(self.db, client_id, **fields)

    def _update_client_record_status(
        self, client_id: int, new_status: ClientStatus
    ) -> None:
        record = self.record_repo.get_by_id(client_id)
        if not record:
            return
        self.record_repo.update_status(record.id, new_status)
        if new_status in {ClientStatus.CLOSED, ClientStatus.FROZEN}:
            VatWorkItemClientStatusService(self.db).cancel_open_by_client_record(
                record.id
            )
            AnnualReportClientStatusService(self.db).cancel_open_by_client_record(
                record.id
            )
            BinderRepository(self.db).archive_in_office_by_client_record(record.id)

    def _cancel_deadlines_on_entity_type_change(
        self, client_id: int, old_entity_type, new_entity_type, actor_id
    ):
        record = self.record_repo.get_by_id(client_id)
        if not record:
            return
        _log.warning(
            "entity_type_changed: client_id=%s old=%s new=%s actor=%s",
            client_id,
            old_entity_type,
            new_entity_type,
            actor_id,
        )
        self._audit.record_update(
            ENTITY_CLIENT,
            client_id,
            actor_id,
            old_value={"entity_type": old_entity_type},
            new_value={"entity_type": new_entity_type},
            note=ACTION_ENTITY_TYPE_CHANGED,
        )
