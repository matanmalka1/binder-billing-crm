from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.models.business import Business
from app.businesses.services.business_service import BusinessService
from app.clients.models.client import Client, IdNumberType
from app.clients.services.client_service import ClientService
from app.common.enums import EntityType, VatType


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
        business_name: str,
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
        business_opened_at: Optional[date] = None,
        business_notes: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> tuple[Client, Business]:
        """
        Create both records in the current DB transaction.

        The caller/session owner is responsible for commit. If any creation step
        raises, the request-level DB dependency rolls back both records.
        """
        normalized_business_name = business_name.strip()
        if not normalized_business_name:
            raise ValueError("יש להזין שם עסק")

        client = self.client_service.create_client(
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
        business = self.business_service.create_business(
            client_id=client.id,
            opened_at=business_opened_at,
            business_name=normalized_business_name,
            notes=business_notes,
            actor_id=actor_id,
        )
        return client, business
