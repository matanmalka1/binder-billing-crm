from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.legal_entity import LegalEntity
from app.common.enums import EntityType, IdNumberType, VatType


class LegalEntityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        id_number: str,
        id_number_type: IdNumberType,
        official_name: str,
        entity_type: Optional[EntityType] = None,
        vat_reporting_frequency: Optional[VatType] = None,
        vat_exempt_ceiling=None,
        advance_rate=None,
    ) -> LegalEntity:
        entity = LegalEntity(
            id_number=id_number,
            id_number_type=id_number_type,
            official_name=official_name,
            entity_type=entity_type,
            vat_reporting_frequency=vat_reporting_frequency,
            vat_exempt_ceiling=vat_exempt_ceiling,
            advance_rate=advance_rate,
        )
        self.db.add(entity)
        self.db.flush()
        return entity

    def get_by_id(self, entity_id: int) -> Optional[LegalEntity]:
        return self.db.query(LegalEntity).filter(LegalEntity.id == entity_id).first()

    def get_by_id_number(self, id_number_type: IdNumberType, id_number: str) -> Optional[LegalEntity]:
        return (
            self.db.query(LegalEntity)
            .filter(
                LegalEntity.id_number_type == id_number_type,
                LegalEntity.id_number == id_number,
            )
            .first()
        )
