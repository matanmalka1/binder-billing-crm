from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.clients.models.client import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
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
        record = (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id == client_id, ClientRecord.deleted_at.is_(None))
            .first()
        )
        if record:
            return record

        client = self._get_active_legacy_client(client_id)
        if not client:
            return None

        legal_entity = self._get_or_create_legacy_legal_entity(client)
        return self._create_legacy_record(client, legal_entity.id)

    def _get_active_legacy_client(self, client_id: int) -> Optional[Client]:
        return (
            self.db.query(Client)
            .filter(Client.id == client_id, Client.deleted_at.is_(None))
            .first()
        )

    def _get_or_create_legacy_legal_entity(self, client: Client) -> LegalEntity:
        legal_entity = (
            self.db.query(LegalEntity)
            .filter(
                LegalEntity.id_number == client.id_number,
                LegalEntity.id_number_type == client.id_number_type,
            )
            .first()
        )
        if legal_entity:
            return legal_entity

        legal_entity = LegalEntity(
            id_number=client.id_number,
            id_number_type=client.id_number_type,
            entity_type=client.entity_type,
            vat_reporting_frequency=client.vat_reporting_frequency,
            vat_exempt_ceiling=client.vat_exempt_ceiling,
            advance_rate=client.advance_rate,
            advance_rate_updated_at=client.advance_rate_updated_at,
        )
        self.db.add(legal_entity)
        self.db.flush()
        return legal_entity

    def _create_legacy_record(self, client: Client, legal_entity_id: int) -> ClientRecord:
        record = ClientRecord(
            id=client.id,
            legal_entity_id=legal_entity_id,
            office_client_number=client.office_client_number,
            accountant_name=client.accountant_name,
            status=client.status,
            created_by=client.created_by,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def update_status(self, client_record_id: int, status: ClientStatus) -> Optional[ClientRecord]:
        record = (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None))
            .first()
        )
        if not record:
            return None
        record.status = status
        self.db.flush()
        return record
