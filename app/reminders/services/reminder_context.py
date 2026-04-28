from typing import Dict, List, Optional, TypedDict

from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.reminders.models.reminder import Reminder
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository

DEADLINE_TYPE_LABELS: Dict[str, str] = {
    "vat": 'מועד מע"מ מתקרב',
    "advance_payment": "מועד מקדמות מתקרב",
    "national_insurance": "מועד ביטוח לאומי מתקרב",
    "annual_report": "מועד דוח שנתי מתקרב",
    "other": "מועד מס מתקרב",
}


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
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
) -> Dict[int, ReminderContext]:
    client_record_ids = list({r.client_record_id for r in items})
    business_ids = list({r.business_id for r in items if r.business_id is not None})
    client_records = ClientRecordRepository(db).list_by_ids(client_record_ids)
    record_by_id = {record.id: record for record in client_records}
    legal_entity_ids = list({record.legal_entity_id for record in client_records})
    legal_entity_by_id = {
        entity.id: entity
        for entity in db.query(LegalEntity).filter(LegalEntity.id.in_(legal_entity_ids)).all()
    } if legal_entity_ids else {}
    businesses = {b.id: b for b in business_repo.list_by_ids(business_ids)} if business_ids else {}
    deadline_label_map = _build_deadline_label_map(items, tax_deadline_repo)
    return {
        r.id: _build_context(r, record_by_id, legal_entity_by_id, businesses, deadline_label_map)
        for r in items
    }


def _build_deadline_label_map(
    items: List[Reminder],
    tax_deadline_repo: Optional[TaxDeadlineRepository],
) -> Dict[int, str]:
    if tax_deadline_repo is None:
        return {}
    result: Dict[int, str] = {}
    for td_id in {r.tax_deadline_id for r in items if r.tax_deadline_id is not None}:
        deadline = tax_deadline_repo.get_by_id(td_id)
        if deadline:
            result[td_id] = DEADLINE_TYPE_LABELS.get(deadline.deadline_type.value, "מועד מס מתקרב")
    return result


def _build_context(r, record_by_id, legal_entity_by_id, businesses, deadline_label_map):
    client_record = record_by_id.get(r.client_record_id)
    legal_entity = legal_entity_by_id.get(client_record.legal_entity_id) if client_record else None
    business = businesses.get(r.business_id) if r.business_id else None
    return ReminderContext(
        client_record_id=r.client_record_id,
        client_name=legal_entity.official_name if legal_entity else f"לקוח #{r.client_record_id}",
        client_id_number=legal_entity.id_number if legal_entity else None,
        office_client_number=client_record.office_client_number if client_record else None,
        business_id=r.business_id,
        business_name=business.business_name if business else None,
        display_label=deadline_label_map.get(r.tax_deadline_id) if r.tax_deadline_id else None,
    )
