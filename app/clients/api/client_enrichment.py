"""Enrichment helpers for ClientResponse — attaches derived fields from related services."""
from sqlalchemy.orm import Session

from app.clients.schemas.client import ClientResponse
from app.binders.services.binder_operations_service import BinderOperationsService


def enrich_single(client_resp: ClientResponse, db: Session) -> ClientResponse:
    """Attach active_binder_number to a single ClientResponse."""
    service = BinderOperationsService(db)
    active = service.get_active_binder_for_client(client_resp.id)
    if active:
        client_resp.active_binder_number = active.binder_number
    return client_resp


def enrich_list(items: list[ClientResponse], db: Session) -> list[ClientResponse]:
    """Bulk-enrich a list of ClientResponse objects."""
    if not items:
        return items
    ids = [c.id for c in items]
    service = BinderOperationsService(db)
    active_binders = service.map_active_binders_for_clients(ids)
    for c in items:
        if c.id in active_binders:
            c.active_binder_number = active_binders[c.id].binder_number
    return items
