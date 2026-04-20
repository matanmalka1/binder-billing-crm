"""Read-side helpers for ClientRecord — full JOIN queries returning ClientRecordResponse."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import PersonLegalEntityLink, PersonLegalEntityRole


def _build_full_join(db: Session):
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


def _row_to_dict(cr: ClientRecord, le: LegalEntity, person: Person | None) -> dict:
    return {
        "id": cr.id,
        "official_name": le.official_name,
        "id_number": le.id_number,
        "id_number_type": le.id_number_type,
        "entity_type": le.entity_type,
        "status": cr.status,
        "office_client_number": cr.office_client_number,
        "accountant_name": cr.accountant_name,
        "notes": cr.notes,
        "vat_reporting_frequency": le.vat_reporting_frequency,
        "vat_exempt_ceiling": le.vat_exempt_ceiling,
        "advance_rate": le.advance_rate,
        "advance_rate_updated_at": le.advance_rate_updated_at,
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
    }


def get_full_record(db: Session, client_record_id: int) -> dict | None:
    """Active ClientRecord fully joined — returns raw dict for schema construction."""
    row = (
        _build_full_join(db)
        .filter(ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None))
        .first()
    )
    if not row:
        return None
    return _row_to_dict(*row)


def get_full_record_including_deleted(db: Session, client_record_id: int) -> dict | None:
    """Same as get_full_record but includes soft-deleted records."""
    row = (
        _build_full_join(db)
        .filter(ClientRecord.id == client_record_id)
        .first()
    )
    if not row:
        return None
    return _row_to_dict(*row)


def get_full_records_bulk(db: Session, client_record_ids: list[int]) -> dict[int, dict]:
    """Bulk fetch — returns {client_record_id: dict} for all given IDs (active only)."""
    if not client_record_ids:
        return {}
    rows = (
        _build_full_join(db)
        .filter(
            ClientRecord.id.in_(client_record_ids),
            ClientRecord.deleted_at.is_(None),
        )
        .all()
    )
    return {cr.id: _row_to_dict(cr, le, person) for cr, le, person in rows}
