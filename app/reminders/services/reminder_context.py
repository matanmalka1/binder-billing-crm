from typing import Dict, List, Optional, TypedDict

from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.reminders.models.reminder import Reminder


class ReminderContext(TypedDict):
    client_record_id: int
    client_name: str
    client_id_number: Optional[str]
    office_client_number: Optional[int]
    business_id: Optional[int]
    business_name: Optional[str]
    display_label: Optional[str]


def build_context_map(
    db,
    business_repo: BusinessRepository,
    items: List[Reminder],
) -> Dict[int, ReminderContext]:
    client_record_ids = list({r.client_record_id for r in items})
    business_ids = list({r.business_id for r in items if r.business_id is not None})
    client_records = ClientRecordRepository(db).list_by_ids(client_record_ids)
    record_by_id = {record.id: record for record in client_records}
    legal_entity_ids = list({record.legal_entity_id for record in client_records})
    legal_entity_by_id = (
        {
            entity.id: entity
            for entity in db.query(LegalEntity)
            .filter(LegalEntity.id.in_(legal_entity_ids))
            .all()
        }
        if legal_entity_ids
        else {}
    )
    businesses = (
        {b.id: b for b in business_repo.list_by_ids(business_ids)}
        if business_ids
        else {}
    )
    return {
        r.id: _build_context(r, record_by_id, legal_entity_by_id, businesses)
        for r in items
    }


def _build_context(r, record_by_id, legal_entity_by_id, businesses):
    client_record = record_by_id.get(r.client_record_id)
    legal_entity = (
        legal_entity_by_id.get(client_record.legal_entity_id) if client_record else None
    )
    business = businesses.get(r.business_id) if r.business_id else None
    return ReminderContext(
        client_record_id=r.client_record_id,
        client_name=legal_entity.official_name
        if legal_entity
        else f"לקוח #{r.client_record_id}",
        client_id_number=legal_entity.id_number if legal_entity else None,
        office_client_number=client_record.office_client_number
        if client_record
        else None,
        business_id=r.business_id,
        business_name=business.business_name if business else None,
        display_label=None,
    )
