from sqlalchemy.orm import Session

from app.clients.enums import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import EntityType, VatType


class ClientVatStatsRepository:
    def __init__(self, db: Session):
        self.db = db

    def _active_base(self):
        return (
            self.db.query(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .filter(
                ClientRecord.deleted_at.is_(None),
                ClientRecord.status == ClientStatus.ACTIVE,
            )
        )

    def count_active_by_vat_type(self, vat_type: VatType) -> int:
        return (
            self._active_base()
            .filter(LegalEntity.vat_reporting_frequency == vat_type)
            .count()
        )

    def count_active_by_entity_and_vat_type(
        self, entity_type: EntityType, vat_type: VatType
    ) -> int:
        return (
            self._active_base()
            .filter(
                LegalEntity.entity_type == entity_type,
                LegalEntity.vat_reporting_frequency == vat_type,
            )
            .count()
        )

    def count_active_exempt(self) -> int:
        return (
            self._active_base()
            .filter(LegalEntity.vat_reporting_frequency == VatType.EXEMPT)
            .count()
        )
