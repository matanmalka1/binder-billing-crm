from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository


class ClientRecordLinkService:
    def __init__(self, db: Session):
        self.db = db

    def get_client_record_by_client_id(self, client_id: int) -> Optional[ClientRecord]:
        client = ClientRepository(self.db).get_by_id(client_id)
        if not client:
            return None
        legal_entity = LegalEntityRepository(self.db).get_by_id_number(
            client.id_number_type,
            client.id_number,
        )
        if not legal_entity:
            return None
        return ClientRecordRepository(self.db).get_by_legal_entity_id(legal_entity.id)
