"""Enrichment helpers for ClientResponse — attaches derived fields from related services."""
from sqlalchemy.orm import Session

from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.schemas.client import ClientResponse
from app.binders.services.binder_operations_service import BinderOperationsService


def _resolve_client_record_id(client_id: int, db: Session) -> int | None:
    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        return None
    legal_entity = LegalEntityRepository(db).get_by_id_number(client.id_number_type, client.id_number)
    if not legal_entity:
        return None
    record = ClientRecordRepository(db).get_by_legal_entity_id(legal_entity.id)
    return record.id if record else None


def enrich_single(client_resp: ClientResponse, db: Session) -> ClientResponse:
    """Attach active_binder_number to a single ClientResponse."""
    service = BinderOperationsService(db)
    client_record_id = _resolve_client_record_id(client_resp.id, db)
    active = service.get_active_binder_for_client(client_record_id) if client_record_id else None
    if active:
        client_resp.active_binder_number = active.binder_number
    return client_resp


def enrich_list(items: list[ClientResponse], db: Session) -> list[ClientResponse]:
    """Bulk-enrich a list of ClientResponse objects."""
    if not items:
        return items
    record_ids = {c.id: _resolve_client_record_id(c.id, db) for c in items}
    service = BinderOperationsService(db)
    active_binders = service.map_active_binders_for_clients(
        [record_id for record_id in record_ids.values() if record_id is not None]
    )
    for c in items:
        client_record_id = record_ids[c.id]
        if client_record_id in active_binders:
            c.active_binder_number = active_binders[client_record_id].binder_number
    return items
