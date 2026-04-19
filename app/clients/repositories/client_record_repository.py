from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.core.exceptions import NotFoundError


class ClientRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        legal_entity_id: int,
        office_client_number: Optional[int] = None,
        accountant_name: Optional[str] = None,
        status: ClientStatus = ClientStatus.ACTIVE,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> ClientRecord:
        record = ClientRecord(
            legal_entity_id=legal_entity_id,
            office_client_number=office_client_number,
            accountant_name=accountant_name,
            status=status,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(record)
        self.db.flush()
        return record

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
