from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository
from app.clients.repositories.client_repository import ClientRepository
from app.search.services.search_filters import matches_signal_type
from app.binders.services.signals_service import SignalsService
from app.binders.services.work_state_service import WorkStateService


class SearchService:
    """Unified search for clients and binders."""

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self.binder_repo = BinderRepository(db)
        self.signals_service = SignalsService(db)

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        binder_number: Optional[str] = None,
        work_state: Optional[str] = None,
        signal_type: Optional[list[str]] = None,
        has_signals: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[dict], int]:
        if reference_date is None:
            reference_date = date.today()

        results = []

        if query or client_name or id_number:
            clients = self.client_repo.list(page=1, page_size=1000)
            for client in clients:
                match = True
                if query:
                    query_lower = query.lower()
                    match = (
                        query_lower in client.full_name.lower()
                        or query_lower in client.id_number
                    )
                if client_name and match:
                    match = client_name.lower() in client.full_name.lower()
                if id_number and match:
                    match = id_number in client.id_number
                if match:
                    results.append(
                        {
                            "result_type": "client",
                            "client_id": client.id,
                            "client_name": client.full_name,
                            "binder_id": None,
                            "binder_number": None,
                            "work_state": None,
                            "signals": [],
                        }
                    )

        if query or binder_number or work_state or signal_type or has_signals is not None:
            binders = self.binder_repo.list_active()
            for binder in binders:
                match = True
                if query:
                    match = query.lower() in binder.binder_number.lower()
                if binder_number and match:
                    match = binder_number.lower() in binder.binder_number.lower()

                current_work_state = WorkStateService.derive_work_state(
                    binder, reference_date, self.db
                )
                current_signals = self.signals_service.compute_binder_signals(
                    binder, reference_date
                )

                if signal_type and match:
                    match = matches_signal_type(current_signals, signal_type)
                if work_state and match:
                    match = current_work_state.value == work_state
                if has_signals is not None and match:
                    match = (len(current_signals) > 0) == has_signals

                if match:
                    client = self.client_repo.get_by_id(binder.client_id)
                    results.append(
                        {
                            "result_type": "binder",
                            "client_id": binder.client_id,
                            "client_name": client.full_name if client else "Unknown",
                            "binder_id": binder.id,
                            "binder_number": binder.binder_number,
                            "work_state": current_work_state.value,
                            "signals": current_signals,
                        }
                    )

        total = len(results)
        offset = (page - 1) * page_size
        return results[offset : offset + page_size], total
