from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories import BinderRepository, ClientRepository
from app.services.signals_service import SignalsService
from app.services.sla_service import SLAService
from app.services.work_state_service import WorkStateService


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
        has_signals: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[dict], int]:
        """
        Search clients and binders with filters.
        
        Returns (results, total).
        """
        if reference_date is None:
            reference_date = date.today()

        results = []

        # Client search
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
                    results.append({
                        "result_type": "client",
                        "client_id": client.id,
                        "client_name": client.full_name,
                        "binder_id": None,
                        "binder_number": None,
                        "work_state": None,
                        "signals": [],
                    })

        # Binder search
        if query or binder_number or work_state or has_signals:
            binders = self.binder_repo.list_active()
            
            for binder in binders:
                match = True
                
                if query:
                    match = query.lower() in binder.binder_number.lower()
                
                if binder_number and match:
                    match = binder_number.lower() in binder.binder_number.lower()
                
                # Compute derived state
                current_work_state = WorkStateService.derive_work_state(
                    binder, reference_date
                )
                current_signals = self.signals_service.compute_binder_signals(
                    binder, reference_date
                )
                
                if work_state and match:
                    match = current_work_state.value == work_state
                
                if has_signals and match:
                    match = len(current_signals) > 0
                
                if match:
                    client = self.client_repo.get_by_id(binder.client_id)
                    results.append({
                        "result_type": "binder",
                        "client_id": binder.client_id,
                        "client_name": client.full_name if client else "Unknown",
                        "binder_id": binder.id,
                        "binder_number": binder.binder_number,
                        "work_state": current_work_state.value,
                        "signals": current_signals,
                    })

        total = len(results)
        offset = (page - 1) * page_size
        return results[offset : offset + page_size], total