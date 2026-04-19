from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.core.exceptions import NotFoundError


class ClientRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_legal_entity_id_by_client_record_id(self, client_record_id: int) -> int:
        """Return legal_entity_id for a ClientRecord, or raise NotFoundError."""
        row = (
            self.db.query(ClientRecord.legal_entity_id)
            .filter(ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None))
            .first()
        )
        if row is None:
            raise NotFoundError(
                f"רשומת לקוח {client_record_id} לא נמצאה",
                "CLIENT_RECORD.NOT_FOUND",
            )
        return row[0]

    def get_by_client_id(self, client_id: int) -> Optional[ClientRecord]:
        """Return the active ClientRecord whose legacy client_id matches, or None.

        Bridges the old clients.id world to client_records during the migration period.
        ClientRecord.id == client_id holds only because the initial schema populated
        client_records with the same PK as their originating clients row.
        """
        return (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id == client_id, ClientRecord.deleted_at.is_(None))
            .first()
        )
