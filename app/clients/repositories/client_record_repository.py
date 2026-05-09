from __future__ import annotations

from typing import Optional

from sqlalchemy import asc, case, desc, func, select
from sqlalchemy.orm import Session

from app.clients.enums import ClientStatus
from app.common.enums import EntityType
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.core.exceptions import NotFoundError
from app.utils.time_utils import utcnow


def _full_record_query(db: Session):
    return (
        db.query(ClientRecord, LegalEntity, Person)
        .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
        .outerjoin(
            PersonLegalEntityLink,
            (PersonLegalEntityLink.legal_entity_id == LegalEntity.id)
            & (PersonLegalEntityLink.role == PersonLegalEntityRole.OWNER),
        )
        .outerjoin(Person, Person.id == PersonLegalEntityLink.person_id)
    )


def _full_record_dict(cr: ClientRecord, le: LegalEntity, person: Person | None) -> dict:
    full_name = person.full_name if person and person.full_name else le.official_name
    return {
        "id": cr.id,
        "full_name": full_name,
        "id_number": le.id_number,
        "id_number_type": le.id_number_type,
        "entity_type": le.entity_type,
        "status": cr.status,
        "office_client_number": cr.office_client_number,
        "accountant_id": cr.accountant_id,
        "notes": cr.notes,
        "vat_reporting_frequency": le.vat_reporting_frequency,
        "advance_payment_frequency": le.advance_payment_frequency,
        "vat_exempt_ceiling": le.vat_exempt_ceiling,
        "advance_rate": le.advance_rate,
        "advance_rate_updated_at": le.advance_rate_updated_at,
        "annual_revenue": le.annual_revenue,
        "phone": person.phone if person else None,
        "email": person.email if person else None,
        "address_street": person.address_street if person else None,
        "address_building_number": person.address_building_number if person else None,
        "address_apartment": person.address_apartment if person else None,
        "address_city": person.address_city if person else None,
        "address_zip_code": person.address_zip_code if person else None,
        "created_at": cr.created_at,
        "updated_at": cr.updated_at,
        "created_by": cr.created_by,
        "deleted_at": cr.deleted_at,
        "deleted_by": cr.deleted_by,
        "restored_at": cr.restored_at,
        "restored_by": cr.restored_by,
    }


def get_full_record(db: Session, client_record_id: int) -> dict | None:
    row = (
        _full_record_query(db)
        .filter(ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None))
        .first()
    )
    return _full_record_dict(*row) if row else None


def get_full_record_including_deleted(
    db: Session, client_record_id: int
) -> dict | None:
    row = _full_record_query(db).filter(ClientRecord.id == client_record_id).first()
    return _full_record_dict(*row) if row else None


def get_full_records_bulk(db: Session, client_record_ids: list[int]) -> dict[int, dict]:
    if not client_record_ids:
        return {}
    rows = (
        _full_record_query(db)
        .filter(
            ClientRecord.id.in_(client_record_ids),
            ClientRecord.deleted_at.is_(None),
        )
        .all()
    )
    return {cr.id: _full_record_dict(cr, le, person) for cr, le, person in rows}


class ClientRecordRepository:
    """
    Data access for ClientRecord + LegalEntity.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── write methods ────────────────────────────────────────────────────────

    def create(
        self,
        *,
        legal_entity_id: int,
        office_client_number: Optional[int] = None,
        accountant_id: Optional[int] = None,
        status: ClientStatus = ClientStatus.ACTIVE,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> ClientRecord:
        record = ClientRecord(
            legal_entity_id=legal_entity_id,
            office_client_number=office_client_number,
            accountant_id=accountant_id,
            status=status,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def update_status(
        self, client_record_id: int, status: ClientStatus
    ) -> Optional[ClientRecord]:
        record = self.db.scalars(
            select(ClientRecord).where(
                ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None)
            )
        ).first()
        if not record:
            return None
        record.status = status
        self.db.flush()
        return record

    def soft_delete(self, client_record_id: int, deleted_by: int) -> bool:
        record = self.db.scalars(
            select(ClientRecord).where(ClientRecord.id == client_record_id)
        ).first()
        if not record:
            return False
        record.deleted_at = utcnow()
        record.deleted_by = deleted_by
        self.db.flush()
        return True

    def restore(
        self, client_record_id: int, restored_by: int
    ) -> Optional[ClientRecord]:
        record = self.db.scalars(
            select(ClientRecord).where(ClientRecord.id == client_record_id)
        ).first()
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
        return self.db.scalars(
            select(ClientRecord).where(
                ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None)
            )
        ).first()

    def get_by_id_including_deleted(
        self, client_record_id: int
    ) -> Optional[ClientRecord]:
        return self.db.scalars(
            select(ClientRecord).where(ClientRecord.id == client_record_id)
        ).first()

    def get_by_legal_entity_id(self, legal_entity_id: int) -> Optional[ClientRecord]:
        return self.db.scalars(
            select(ClientRecord).where(
                ClientRecord.legal_entity_id == legal_entity_id,
                ClientRecord.deleted_at.is_(None),
            )
        ).first()

    def get_legal_entity_id_by_client_record_id(self, client_record_id: int) -> int:
        """Return legal_entity_id for a ClientRecord, or raise NotFoundError."""
        row = self.db.execute(
            select(ClientRecord.legal_entity_id).where(
                ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None)
            )
        ).first()
        if row is None:
            raise NotFoundError(
                f"רשומת לקוח {client_record_id} לא נמצאה",
                "CLIENT_RECORD.NOT_FOUND",
            )
        return row[0]

    # ── active-record lookups by id_number (via LegalEntity JOIN) ────────────

    def get_active_by_id_number(self, id_number: str) -> list[ClientRecord]:
        """Active ClientRecords whose LegalEntity has the given id_number."""
        return self.db.scalars(
            select(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .where(
                LegalEntity.id_number == id_number, ClientRecord.deleted_at.is_(None)
            )
        ).all()

    def get_deleted_by_id_number(self, id_number: str) -> list[ClientRecord]:
        """Soft-deleted ClientRecords whose LegalEntity has the given id_number."""
        return self.db.scalars(
            select(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .where(
                LegalEntity.id_number == id_number, ClientRecord.deleted_at.isnot(None)
            )
            .order_by(ClientRecord.deleted_at.desc())
        ).all()

    # ── batch lookups ────────────────────────────────────────────────────────

    def list_by_ids(self, client_record_ids: list[int]) -> list[ClientRecord]:
        if not client_record_ids:
            return []
        return self.db.scalars(
            select(ClientRecord).where(
                ClientRecord.id.in_(client_record_ids),
                ClientRecord.deleted_at.is_(None),
            )
        ).all()

    # ── list / count / search (join LegalEntity for name/id_number filters) ──

    _SORTABLE_FIELDS = {
        "official_name": LegalEntity.official_name,
        "created_at": ClientRecord.created_at,
        "status": ClientRecord.status,
    }

    _ENTITY_TYPE_ORDER = ["osek_patur", "osek_murshe", "company_ltd", "employee"]

    def _active_query(self):
        return (
            select(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .where(ClientRecord.deleted_at.is_(None))
        )

    def _apply_list_filters(
        self, stmt, search=None, status=None, accountant_id=None, entity_type=None
    ):
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                LegalEntity.official_name.ilike(term)
                | LegalEntity.id_number.ilike(term)
            )
        if status:
            stmt = stmt.where(ClientRecord.status == status)
        if accountant_id is not None:
            stmt = stmt.where(ClientRecord.accountant_id == accountant_id)
        if entity_type is not None:
            stmt = stmt.where(LegalEntity.entity_type == entity_type)
        return stmt

    def list(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        accountant_id: Optional[int] = None,
        entity_type: Optional[EntityType] = None,
        sort_by: str = "official_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> list[ClientRecord]:
        stmt = self._apply_list_filters(
            self._active_query(), search, status, accountant_id, entity_type
        )
        if sort_by == "entity_type":
            order_map = {v: i for i, v in enumerate(self._ENTITY_TYPE_ORDER)}
            sort_col = case(order_map, value=LegalEntity.entity_type)
        else:
            sort_col = self._SORTABLE_FIELDS.get(sort_by, LegalEntity.official_name)
        stmt = stmt.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
        offset = (page - 1) * page_size
        return list(self.db.scalars(stmt.offset(offset).limit(page_size)).all())

    def count(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        accountant_id: Optional[int] = None,
        entity_type: Optional[EntityType] = None,
    ) -> int:
        count_stmt = self._apply_list_filters(
            select(func.count(ClientRecord.id))
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .where(ClientRecord.deleted_at.is_(None)),
            search,
            status,
            accountant_id,
            entity_type,
        )
        return self.db.scalar(count_stmt)

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        entity_type: Optional[EntityType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ClientRecord], int]:
        """Cross-domain search by name / id_number / status / entity_type."""
        stmt = self._active_query()
        if query:
            term = f"%{query.strip()}%"
            stmt = stmt.where(
                LegalEntity.official_name.ilike(term)
                | LegalEntity.id_number.ilike(term)
            )
        if client_name:
            stmt = stmt.where(
                LegalEntity.official_name.ilike(f"%{client_name.strip()}%")
            )
        if id_number:
            stmt = stmt.where(LegalEntity.id_number.ilike(f"%{id_number.strip()}%"))
        if status:
            stmt = stmt.where(ClientRecord.status == status)
        if entity_type:
            stmt = stmt.where(LegalEntity.entity_type == entity_type)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        offset = (page - 1) * page_size
        items = list(
            self.db.scalars(
                stmt.order_by(LegalEntity.official_name.asc())
                .offset(offset)
                .limit(page_size)
            ).all()
        )
        return items, total

    def list_all(self) -> list[ClientRecord]:
        """All active ClientRecords ordered by official_name."""
        return list(
            self.db.scalars(
                self._active_query().order_by(LegalEntity.official_name.asc())
            ).all()
        )

    def count_by_status(self) -> dict[ClientStatus, int]:
        """Active ClientRecords grouped by status."""
        rows = self.db.execute(
            select(ClientRecord.status, func.count(ClientRecord.id))
            .where(ClientRecord.deleted_at.is_(None))
            .group_by(ClientRecord.status)
        ).all()
        return {status: count for status, count in rows}

    def get_next_office_client_number(self) -> int:
        current_max = self.db.scalar(
            select(func.max(ClientRecord.office_client_number))
        )
        return 1 if current_max is None else current_max + 1
