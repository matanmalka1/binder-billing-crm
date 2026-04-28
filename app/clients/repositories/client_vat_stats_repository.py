from sqlalchemy.orm import Session

from app.clients.enums import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import VatType


class ClientVatStatsRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_active_by_vat_type(self, vat_type: VatType) -> int:
        return (
            self.db.query(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .filter(
                ClientRecord.deleted_at.is_(None),
                ClientRecord.status == ClientStatus.ACTIVE,
                LegalEntity.vat_reporting_frequency == vat_type,
            )
            .count()
        )
