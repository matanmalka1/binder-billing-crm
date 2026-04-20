from typing import Optional

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from app.clients.enums import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.core.exceptions import NotFoundError
from app.utils.time_utils import utcnow


class ClientRecordRepository:
    """
    Data access for ClientRecord + LegalEntity.

    Existing Client-based callers continue to use ClientRepository (which
    delegates to this class after step 5.8). New callers should use this
    directly. Return-type swap from Client → ClientRecord happens in step 5.6.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── write methods ────────────────────────────────────────────────────────

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

    def soft_delete(self, client_record_id: int, deleted_by: int) -> bool:
        record = (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id == client_record_id)
            .first()
        )
        if not record:
            return False
        record.deleted_at = utcnow()
        record.deleted_by = deleted_by
        self.db.flush()
        return True

    def restore(self, client_record_id: int, restored_by: int) -> Optional[ClientRecord]:
        record = (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id == client_record_id)
            .first()
        )
        if not record or record.deleted_at is None:
            return None
        record.deleted_at = None
        record.deleted_by = None
        record.restored_at = utcnow()
        record.restored_by = restored_by
        self.db.flush()
        return record

    # ── single-record lookups ────────────────────────────────────────────────

    def get_by_id(self, client_record_id: int) -> Optional[ClientRecord]:
        return (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None))
            .first()
        )

    def get_by_id_including_deleted(self, client_record_id: int) -> Optional[ClientRecord]:
        return (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id == client_record_id)
            .first()
        )

    def get_by_legal_entity_id(self, legal_entity_id: int) -> Optional[ClientRecord]:
        return (
            self.db.query(ClientRecord)
            .filter(
                ClientRecord.legal_entity_id == legal_entity_id,
                ClientRecord.deleted_at.is_(None),
            )
            .first()
        )

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

    # ── active-record lookups by id_number (via LegalEntity JOIN) ────────────

    def get_active_by_id_number(self, id_number: str) -> list[ClientRecord]:
        """Active ClientRecords whose LegalEntity has the given id_number."""
        return (
            self.db.query(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .filter(LegalEntity.id_number == id_number, ClientRecord.deleted_at.is_(None))
            .all()
        )

    def get_deleted_by_id_number(self, id_number: str) -> list[ClientRecord]:
        """Soft-deleted ClientRecords whose LegalEntity has the given id_number."""
        return (
            self.db.query(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .filter(LegalEntity.id_number == id_number, ClientRecord.deleted_at.isnot(None))
            .order_by(ClientRecord.deleted_at.desc())
            .all()
        )

    # ── batch lookups ────────────────────────────────────────────────────────

    def list_by_ids(self, client_record_ids: list[int]) -> list[ClientRecord]:
        if not client_record_ids:
            return []
        return (
            self.db.query(ClientRecord)
            .filter(ClientRecord.id.in_(client_record_ids), ClientRecord.deleted_at.is_(None))
            .all()
        )

    # ── list / count / search (join LegalEntity for name/id_number filters) ──

    _SORTABLE_FIELDS = {
        "official_name": LegalEntity.official_name,
        "created_at": ClientRecord.created_at,
        "status": ClientRecord.status,
    }

    def _active_query(self):
        return (
            self.db.query(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .filter(ClientRecord.deleted_at.is_(None))
        )

    def _apply_list_filters(self, query, search=None, status=None):
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                LegalEntity.official_name.ilike(term) | LegalEntity.id_number.ilike(term)
            )
        if status:
            query = query.filter(ClientRecord.status == status)
        return query

    def list(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        sort_by: str = "official_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> list[ClientRecord]:
        query = self._apply_list_filters(self._active_query(), search, status)
        col = self._SORTABLE_FIELDS.get(sort_by, LegalEntity.official_name)
        query = query.order_by(desc(col) if sort_order == "desc" else asc(col))
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()

    def count(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
    ) -> int:
        return self._apply_list_filters(self._active_query(), search, status).count()

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ClientRecord], int]:
        """Cross-domain search by name / id_number."""
        q = self._active_query()
        if query:
            term = f"%{query.strip()}%"
            q = q.filter(LegalEntity.official_name.ilike(term) | LegalEntity.id_number.ilike(term))
        if client_name:
            q = q.filter(LegalEntity.official_name.ilike(f"%{client_name.strip()}%"))
        if id_number:
            q = q.filter(LegalEntity.id_number.ilike(f"%{id_number.strip()}%"))
        total = q.count()
        offset = (page - 1) * page_size
        items = q.order_by(LegalEntity.official_name.asc()).offset(offset).limit(page_size).all()
        return items, total

    def list_all(self) -> list[ClientRecord]:
        """All active ClientRecords ordered by official_name."""
        return (
            self._active_query()
            .order_by(LegalEntity.official_name.asc())
            .all()
        )

    def count_by_status(self) -> dict[ClientStatus, int]:
        """Active ClientRecords grouped by status."""
        rows = (
            self.db.query(ClientRecord.status, func.count(ClientRecord.id))
            .filter(ClientRecord.deleted_at.is_(None))
            .group_by(ClientRecord.status)
            .all()
        )
        return {status: count for status, count in rows}

    def get_next_office_client_number(self) -> int:
        current_max = self.db.query(func.max(ClientRecord.office_client_number)).scalar()
        return 1 if current_max is None else current_max + 1
