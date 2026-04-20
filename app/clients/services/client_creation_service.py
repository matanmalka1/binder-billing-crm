import json
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.actions.obligation_orchestrator import generate_client_obligations
from app.audit.constants import ACTION_CREATED, ENTITY_CLIENT
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.binders.services.client_onboarding_service import create_initial_binder
from app.clients.models.client import Client, IdNumberType
from app.clients.models.client_record import ClientRecord
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.clients.repositories.person_repository import PersonRepository
from app.clients.services.messages import (
    CLIENT_ID_NUMBER_CONFLICT,
    CLIENT_ID_NUMBER_DELETED,
    CLIENT_ID_NUMBER_EXISTS,
    CLIENT_OFFICE_NUMBER_CONFLICT,
)
from app.common.enums import EntityType, VatType
from app.core.exceptions import ConflictError
# TODO 5.8: change return shape to (ClientRecord,) after Client deletion

class ClientCreationService:
    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self._audit = EntityAuditLogRepository(db)

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
        if self.client_repo.get_active_by_id_number(id_number):
            raise ConflictError(CLIENT_ID_NUMBER_EXISTS.format(id_number=id_number), "CLIENT.CONFLICT")
        if self.client_repo.get_deleted_by_id_number(id_number):
            raise ConflictError(
                CLIENT_ID_NUMBER_DELETED.format(id_number=id_number), "CLIENT.DELETED_EXISTS"
            )

        le_repo = LegalEntityRepository(self.db)
        if le_repo.get_by_id_number(id_number_type, id_number):
            raise ConflictError(CLIENT_ID_NUMBER_EXISTS.format(id_number=id_number), "CLIENT.CONFLICT")

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
                official_name=full_name,
                entity_type=entity_type,
                vat_reporting_frequency=vat_reporting_frequency,
                vat_exempt_ceiling=vat_exempt_ceiling,
                advance_rate=advance_rate,
            )
        PersonRepository(self.db).ensure_owner(
            legal_entity_id=legal_entity.id, full_name=full_name, id_number=id_number,
            id_number_type=id_number_type, phone=phone, email=email,
            address_street=address_street, address_building_number=address_building_number,
            address_apartment=address_apartment, address_city=address_city,
            address_zip_code=address_zip_code,
        )
        record_repo = ClientRecordRepository(self.db)
        client_record = record_repo.get_by_legal_entity_id(legal_entity.id)
        if not client_record:
            client_record = record_repo.create(
                legal_entity_id=legal_entity.id,
                office_client_number=client.office_client_number,
                accountant_name=accountant_name,
                created_by=actor_id,
            )
        create_initial_binder(self.db, client_record, actor_id)
        generate_client_obligations(
            self.db, client.id, actor_id=actor_id, entity_type=entity_type, best_effort=False,
        )
        if actor_id:
            self._audit.append(
                entity_type=ENTITY_CLIENT,
                entity_id=client.id,
                performed_by=actor_id,
                action=ACTION_CREATED,
                new_value=json.dumps({"full_name": full_name, "id_number": id_number}),
            )
        return client, client_record

    def _create_client_with_generated_office_number(self, **kwargs) -> Client:
        id_number = kwargs["id_number"]
        actor_id = kwargs.pop("actor_id", None)
        for attempt in range(3):
            savepoint = self.db.begin_nested()
            try:
                client = self.client_repo.create(
                    office_client_number=self.client_repo.get_next_office_client_number(),
                    created_by=actor_id,
                    **kwargs,
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
