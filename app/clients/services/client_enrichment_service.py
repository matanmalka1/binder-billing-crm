from sqlalchemy.orm import Session

from app.binders.services.binder_operations_service import BinderOperationsService
from app.clients.schemas.client_record_response import ClientRecordResponse


class ClientEnrichmentService:
    def __init__(self, db: Session):
        self._binder_service = BinderOperationsService(db)

    def enrich_single(self, response: ClientRecordResponse) -> ClientRecordResponse:
        active = self._binder_service.get_active_binder_for_client(response.id)
        if active:
            response.active_binder_number = active.binder_number
        return response

    def enrich_list(self, items: list[ClientRecordResponse]) -> list[ClientRecordResponse]:
        if not items:
            return items
        active_binders = self._binder_service.map_active_binders_for_clients([c.id for c in items])
        for client in items:
            if client.id in active_binders:
                client.active_binder_number = active_binders[client.id].binder_number
        return items
