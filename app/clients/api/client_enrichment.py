"""Enrichment helpers for ClientRecordResponse — attaches derived fields."""
from sqlalchemy.orm import Session

from app.clients.schemas.client_record_response import ClientRecordResponse
from app.binders.services.binder_operations_service import BinderOperationsService


def enrich_single(response: ClientRecordResponse, db: Session) -> ClientRecordResponse:
    """Attach active_binder_number to a single ClientRecordResponse."""
    service = BinderOperationsService(db)
    active = service.get_active_binder_for_client(response.id)
    if active:
        response.active_binder_number = active.binder_number
    return response


def enrich_list(items: list[ClientRecordResponse], db: Session) -> list[ClientRecordResponse]:
    """Bulk-enrich a list of ClientRecordResponse objects."""
    if not items:
        return items
    record_ids = [c.id for c in items]
    service = BinderOperationsService(db)
    active_binders = service.map_active_binders_for_clients(record_ids)
    for c in items:
        if c.id in active_binders:
            c.active_binder_number = active_binders[c.id].binder_number
    return items
