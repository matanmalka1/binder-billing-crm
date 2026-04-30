from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.models.business import Business
from app.businesses.services.business_service import BusinessService
from app.clients.constants import UNSUPPORTED_EMPLOYEE_CREATE_ERROR
from app.clients.create_policy import (
    normalize_vat_exempt_ceiling,
    normalize_vat_reporting_frequency,
)
from app.clients.models.client_record import ClientRecord
from app.clients.schemas.client import ActiveClientSummary, ClientConflictInfo, DeletedClientSummary
from app.clients.services.client_service import ClientService
from app.common.enums import EntityType, IdNumberType, VatType
from app.core.exceptions import ConflictError


class ClientCreationConflictError(Exception):
    def __init__(self, detail: dict):
        super().__init__(detail.get("detail"))
        self.detail = detail


class CreateClientService:
    """Coordinate creation of a reporting entity and its first business."""

    def __init__(self, db: Session):
        self.db = db
        self.client_service = ClientService(db)
        self.business_service = BusinessService(db)

    def create_client(
        self,
        *,
        full_name: str,
        id_number: str,
        business_name: Optional[str] = None,
        id_number_type: IdNumberType = IdNumberType.INDIVIDUAL, # type: ignore
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
        accountant_id: Optional[int] = None,
        business_opened_at: Optional[date] = None,
        business_notes: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> tuple[ClientRecord, Business]:
        """
        Create all records in the current DB transaction.

        The caller/session owner is responsible for commit. If any creation step
        raises, the request-level DB dependency rolls back all records.
        """
        normalized_business_name = (business_name or '').strip() or full_name.strip()
        if entity_type == EntityType.EMPLOYEE:
            raise ValueError(UNSUPPORTED_EMPLOYEE_CREATE_ERROR)

        normalized_vat_frequency = normalize_vat_reporting_frequency(entity_type, vat_reporting_frequency)
        normalized_vat_ceiling = normalize_vat_exempt_ceiling(entity_type)

        try:
            client_record = self.client_service.create_client(
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
                vat_reporting_frequency=normalized_vat_frequency,
                vat_exempt_ceiling=normalized_vat_ceiling,
                advance_rate=advance_rate,
                accountant_id=accountant_id,
                actor_id=actor_id,
            )
        except ConflictError as exc:
            if exc.code not in {"CLIENT.CONFLICT", "CLIENT.DELETED_EXISTS"}:
                raise
            raise ClientCreationConflictError(self._client_conflict_detail(id_number, exc)) from exc
        business = self.business_service.create_business_for_client_record(
            client_record_id=client_record.id,
            opened_at=business_opened_at,
            business_name=normalized_business_name,
            notes=business_notes,
            actor_id=actor_id,
        )
        return client_record, business

    def _client_conflict_detail(self, id_number: str, error: ConflictError) -> dict:
        conflict_info = self.client_service.get_conflict_info(id_number)
        conflict = ClientConflictInfo(
            id_number=id_number,
            active_clients=[
                ActiveClientSummary.model_validate(c)
                for c in conflict_info["active_clients"]
            ],
            deleted_clients=[
                DeletedClientSummary.model_validate(c)
                for c in conflict_info["deleted_clients"]
            ],
        )
        return {
            "error": error.code,
            "detail": str(error),
            "conflict": conflict.model_dump(mode="json"),
        }
