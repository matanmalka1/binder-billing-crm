import json
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

_log = logging.getLogger(__name__)

from app.audit.constants import ACTION_CREATED, ACTION_DELETED, ACTION_RESTORED, ACTION_UPDATED, ENTITY_CLIENT
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.models.client import Client, IdNumberType
from app.users.models.user import UserRole
from app.clients.models.client import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.common.enums import EntityType, VatType
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.binders.services.client_onboarding_service import create_initial_binder
from app.actions.obligation_orchestrator import generate_client_obligations, obligation_fields_changed
from app.clients.services.client_query_service import ClientQueryService
from app.clients.services.messages import (
    CLIENT_ID_NUMBER_ACTIVE_EXISTS,
    CLIENT_ID_NUMBER_CONFLICT,
    CLIENT_ID_NUMBER_DELETED,
    CLIENT_ID_NUMBER_EXISTS,
    CLIENT_NOT_DELETED,
    CLIENT_NOT_FOUND,
    CLIENT_OFFICE_NUMBER_CONFLICT,
)
from app.core.exceptions import ConflictError, NotFoundError, ForbiddenError
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.vat_reports.repositories.vat_work_item_write_repository import VatWorkItemWriteRepository


class ClientService:
    """
    Client identity management.
    עסקים (Business) מנוהלים ב-BusinessService.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self._audit = EntityAuditLogRepository(db)
        self._query = ClientQueryService(db)

    def create_client(
        self,
        full_name: str,
        id_number: str,
        id_number_type: IdNumberType = IdNumberType.INDIVIDUAL,
        entity_type: Optional[EntityType] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address_street: Optional[str] = None,
        address_building_number: Optional[str] = None,
        address_apartment: Optional[str] = None,
        address_city: Optional[str] = None,
        address_zip_code: Optional[str] = None,
        vat_reporting_frequency: Optional[VatType] = None,
        vat_exempt_ceiling=None,
        advance_rate=None,
        accountant_name: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> tuple[Client, ClientRecord]:
        active_clients = self.client_repo.get_active_by_id_number(id_number)
        if active_clients:
            raise ConflictError(
                CLIENT_ID_NUMBER_EXISTS.format(id_number=id_number),
                "CLIENT.CONFLICT",
            )

        deleted_clients = self.client_repo.get_deleted_by_id_number(id_number)
        if deleted_clients:
            raise ConflictError(
                CLIENT_ID_NUMBER_DELETED.format(id_number=id_number),
                "CLIENT.DELETED_EXISTS",
            )

        le_repo = LegalEntityRepository(self.db)
        if le_repo.get_by_id_number(id_number_type, id_number):
            raise ConflictError(
                CLIENT_ID_NUMBER_EXISTS.format(id_number=id_number),
                "CLIENT.CONFLICT",
            )

        client = self._create_client_with_generated_office_number(
            full_name=full_name,
            id_number=id_number,
            id_number_type=id_number_type,
            entity_type=entity_type,
            phone=phone,
            email=email,
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
            vat_reporting_frequency=vat_reporting_frequency,
            vat_exempt_ceiling=vat_exempt_ceiling,
            advance_rate=advance_rate,
            accountant_name=accountant_name,
            actor_id=actor_id,
        )

        legal_entity = le_repo.get_by_id_number(id_number_type, id_number)
        if not legal_entity:
            legal_entity = le_repo.create(
                id_number=id_number,
                id_number_type=id_number_type,
                entity_type=entity_type,
                vat_reporting_frequency=vat_reporting_frequency,
                vat_exempt_ceiling=vat_exempt_ceiling,
                advance_rate=advance_rate,
            )
        record_repo = ClientRecordRepository(self.db)
        client_record = record_repo.get_by_client_id(client.id) or record_repo.create(
            legal_entity_id=legal_entity.id,
            office_client_number=client.office_client_number,
            accountant_name=accountant_name,
            created_by=actor_id,
        )

        create_initial_binder(self.db, client, actor_id, client_record_id=client_record.id)
        generate_client_obligations(
            self.db, client.id, actor_id=actor_id, entity_type=entity_type, best_effort=False,
        )
        if actor_id:
            self._audit.append(
                entity_type=ENTITY_CLIENT, entity_id=client.id,
                performed_by=actor_id, action=ACTION_CREATED,
                new_value=json.dumps({"full_name": full_name, "id_number": id_number}),
            )
        return client, client_record

    def _create_client_with_generated_office_number(
        self,
        *,
        full_name: str,
        id_number: str,
        id_number_type: IdNumberType,
        entity_type: Optional[EntityType],
        phone: Optional[str],
        email: Optional[str],
        address_street: Optional[str],
        address_building_number: Optional[str],
        address_apartment: Optional[str],
        address_city: Optional[str],
        address_zip_code: Optional[str],
        vat_reporting_frequency: Optional[VatType],
        vat_exempt_ceiling,
        advance_rate,
        accountant_name: Optional[str],
        actor_id: Optional[int],
    ) -> Client:
        for attempt in range(3):
            office_client_number = self.client_repo.get_next_office_client_number()
            savepoint = self.db.begin_nested()
            try:
                client = self.client_repo.create(
                    full_name=full_name,
                    id_number=id_number,
                    id_number_type=id_number_type,
                    entity_type=entity_type,
                    phone=phone,
                    email=email,
                    address_street=address_street,
                    address_building_number=address_building_number,
                    address_apartment=address_apartment,
                    address_city=address_city,
                    address_zip_code=address_zip_code,
                    vat_reporting_frequency=vat_reporting_frequency,
                    vat_exempt_ceiling=vat_exempt_ceiling,
                    advance_rate=advance_rate,
                    accountant_name=accountant_name,
                    office_client_number=office_client_number,
                    created_by=actor_id,
                )
                savepoint.commit()
                return client
            except IntegrityError as exc:
                savepoint.rollback()
                err_str = str(exc.orig).lower() if exc.orig else ""
                if "id_number" in err_str or "ix_clients_id_number" in err_str:
                    raise ConflictError(
                        CLIENT_ID_NUMBER_CONFLICT.format(id_number=id_number), "CLIENT.CONFLICT"
                    ) from exc
                if attempt == 2:
                    break

        raise ConflictError(CLIENT_OFFICE_NUMBER_CONFLICT, "OFFICE_NUMBER.CONFLICT")

    def get_client_or_raise(self, client_id: int) -> Client:
        _log.warning("DEPRECATED: get_client_or_raise reads legacy Client model. Migrate to ClientRecord (Layer 2).")
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        return client

    def update_client(self, client_id: int, actor_id: Optional[int] = None, actor_role=None, **fields) -> Client:
        """Update client identity fields (name, phone, email, address)."""
        existing = self.get_client_or_raise(client_id)
        new_status = fields.get("status")
        new_entity_type = fields.get("entity_type")
        old_entity_type = existing.entity_type
        entity_type_changing = (
            new_entity_type is not None and new_entity_type != old_entity_type
        )
        if entity_type_changing:
            if actor_role != UserRole.ADVISOR:
                raise ForbiddenError("שינוי סוג ישות מותר לרואה חשבון בלבד", "CLIENT.ENTITY_TYPE_CHANGE_FORBIDDEN")
        old_snapshot = {k: getattr(existing, k, None) for k in fields if hasattr(existing, k)}
        updated = self.client_repo.update(client_id, **fields)
        if new_status is not None:
            self._update_client_record_status(client_id, new_status)
        if entity_type_changing:
            self._cancel_deadlines_on_entity_type_change(
                client_id=client_id,
                old_entity_type=old_entity_type,
                new_entity_type=new_entity_type,
                actor_id=actor_id,
            )
        if obligation_fields_changed(fields):
            generate_client_obligations(
                self.db, client_id, actor_id=actor_id,
                entity_type=getattr(updated, "entity_type", None),
                best_effort=True,
            )
        new_snapshot = {k: getattr(updated, k, None) for k in fields if hasattr(updated, k)}
        self._audit.append(
            entity_type=ENTITY_CLIENT, entity_id=client_id,
            performed_by=actor_id, action=ACTION_UPDATED,
            old_value=json.dumps({k: str(v) if v is not None else None for k, v in old_snapshot.items()}),
            new_value=json.dumps({k: str(v) if v is not None else None for k, v in new_snapshot.items()}),
        )
        return updated

    def _update_client_record_status(self, client_id: int, new_status: ClientStatus) -> None:
        record_repo = ClientRecordRepository(self.db)
        record = record_repo.get_by_client_id(client_id)
        if not record:
            return
        record_repo.update_status(record.id, new_status)
        if new_status in {ClientStatus.CLOSED, ClientStatus.FROZEN}:
            ReminderRepository(self.db).cancel_pending_by_client_record(record.id)
            TaxDeadlineRepository(self.db).cancel_pending_by_client_record(record.id)
            VatWorkItemWriteRepository(self.db).cancel_open_by_client_record(record.id)
            AnnualReportReportRepository(self.db).cancel_open_by_client_record(record.id)
            BinderRepository(self.db).archive_in_office_by_client_record(record.id)

    def _cancel_deadlines_on_entity_type_change(
        self, client_id: int, old_entity_type, new_entity_type, actor_id: Optional[int]
    ) -> None:
        record = ClientRecordRepository(self.db).get_by_client_id(client_id)
        if not record:
            return
        deadline_repo = TaxDeadlineRepository(self.db)
        canceled = deadline_repo.cancel_pending_by_client_record(record.id)
        _log.warning(
            "entity_type_changed: client_id=%s old=%s new=%s canceled_deadlines=%s actor=%s",
            client_id, old_entity_type, new_entity_type, canceled, actor_id,
        )
        self._audit.append(
            entity_type=ENTITY_CLIENT, entity_id=client_id,
            performed_by=actor_id, action="entity_type_changed",
            old_value=str(old_entity_type),
            new_value=str(new_entity_type),
        )

    def delete_client(self, client_id: int, actor_id: int) -> None:
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client or client.deleted_at is not None:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        self.client_repo.soft_delete(client_id, deleted_by=actor_id)
        self._audit.append(
            entity_type=ENTITY_CLIENT, entity_id=client_id,
            performed_by=actor_id, action=ACTION_DELETED,
        )

    def restore_client(self, client_id: int, actor_id: int) -> Client:
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        if client.deleted_at is None:
            raise ConflictError(CLIENT_NOT_DELETED, "CLIENT.NOT_DELETED")

        active = self.client_repo.get_active_by_id_number(client.id_number)
        if active:
            raise ConflictError(
                CLIENT_ID_NUMBER_ACTIVE_EXISTS.format(id_number=client.id_number),
                "CLIENT.CONFLICT",
            )

        restored = self.client_repo.restore(client_id, restored_by=actor_id)
        if not restored:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        self._audit.append(
            entity_type=ENTITY_CLIENT, entity_id=client_id,
            performed_by=actor_id, action=ACTION_RESTORED,
        )
        return restored

    # ─── Query delegation ────────────────────────────────────────────────────

    def list_clients(self, search=None, status=None, sort_by="full_name", sort_order="asc", page=1, page_size=20):
        return self._query.list_clients(
            search=search, status=status, sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size,
        )

    def get_client_stats(self):
        return self._query.get_client_stats()

    def list_all_clients(self):
        return self._query.list_all_clients()

    def get_conflict_info(self, id_number: str) -> dict:
        return self._query.get_conflict_info(id_number)
