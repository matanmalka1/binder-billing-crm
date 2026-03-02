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

        # Binder-only derived-state filters need full binder list (in-memory by design)
        binder_derived_filter = work_state or signal_type or has_signals is not None

        # --- Client search: DB-level filtering ---
        if query or client_name or id_number:
            if not binder_derived_filter and not binder_number:
                # Pure client search: paginate at DB level
                clients, total = self.client_repo.search(
                    query=query,
                    client_name=client_name,
                    id_number=id_number,
                    page=page,
                    page_size=page_size,
                )
                return [
                    {
                        "result_type": "client",
                        "client_id": c.id,
                        "client_name": c.full_name,
                        "binder_id": None,
                        "binder_number": None,
                        "work_state": None,
                        "signals": [],
                    }
                    for c in clients
                ], total

        # --- Mixed / binder-filtered search: build full result set then paginate ---
        results: list[dict] = []

        if query or client_name or id_number:
            all_clients, _ = self.client_repo.search(
                query=query,
                client_name=client_name,
                id_number=id_number,
            )
            for c in all_clients:
                results.append(
                    {
                        "result_type": "client",
                        "client_id": c.id,
                        "client_name": c.full_name,
                        "binder_id": None,
                        "binder_number": None,
                        "work_state": None,
                        "signals": [],
                    }
                )

        if query or binder_number or binder_derived_filter:
            # binder_number filter pushed to DB; work_state/signal_type stay in Python
            db_binder_number = binder_number or (query if not (client_name or id_number) else None)
            binders = self.binder_repo.list_active(binder_number=db_binder_number)
            for binder in binders:
                current_work_state = WorkStateService.derive_work_state(
                    binder, reference_date, self.db
                )
                current_signals = self.signals_service.compute_binder_signals(
                    binder, reference_date
                )

                match = True
                if signal_type:
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
        return results[offset: offset + page_size], total
