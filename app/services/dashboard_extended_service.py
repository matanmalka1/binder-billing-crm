from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Binder, ChargeStatus
from app.repositories import BinderRepository, ChargeRepository, ClientRepository
from app.services.signals_service import SignalsService
from app.services.sla_service import SLAService
from app.services.work_state_service import WorkStateService


class DashboardExtendedService:
    """Sprint 6 dashboard extensions for operational UX."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_repo = ClientRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.signals_service = SignalsService(db)

    def get_work_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[dict], int]:
        """Get work queue with binders needing attention."""
        if reference_date is None:
            reference_date = date.today()

        binders = self.binder_repo.list_active()
        
        items = []
        for binder in binders:
            client = self.client_repo.get_by_id(binder.client_id)
            if not client:
                continue

            work_state = WorkStateService.derive_work_state(binder, reference_date)
            signals = self.signals_service.compute_binder_signals(binder, reference_date)
            
            items.append({
                "binder_id": binder.id,
                "client_id": client.id,
                "client_name": client.full_name,
                "binder_number": binder.binder_number,
                "work_state": work_state.value,
                "signals": signals,
                "days_since_received": (reference_date - binder.received_at).days,
                "expected_return_at": binder.expected_return_at,
            })

        total = len(items)
        offset = (page - 1) * page_size
        return items[offset:offset + page_size], total

    def get_alerts(
        self,
        reference_date: Optional[date] = None,
    ) -> list[dict]:
        """Get active alerts (overdue, near SLA, missing docs)."""
        if reference_date is None:
            reference_date = date.today()

        alerts = []
        binders = self.binder_repo.list_active()

        for binder in binders:
            client = self.client_repo.get_by_id(binder.client_id)
            if not client:
                continue

            # Overdue alert
            if SLAService.is_overdue(binder, reference_date):
                alerts.append({
                    "binder_id": binder.id,
                    "client_id": client.id,
                    "client_name": client.full_name,
                    "binder_number": binder.binder_number,
                    "alert_type": "overdue",
                    "days_overdue": SLAService.days_overdue(binder, reference_date),
                    "days_remaining": None,
                })

            # Near SLA alert
            elif SLAService.is_approaching_sla(binder, reference_date):
                alerts.append({
                    "binder_id": binder.id,
                    "client_id": client.id,
                    "client_name": client.full_name,
                    "binder_number": binder.binder_number,
                    "alert_type": "near_sla",
                    "days_overdue": None,
                    "days_remaining": SLAService.days_remaining(binder, reference_date),
                })

        return alerts

    def get_attention_items(
        self,
        reference_date: Optional[date] = None,
    ) -> list[dict]:
        """Get items requiring attention (idle, ready, unpaid)."""
        if reference_date is None:
            reference_date = date.today()

        items = []
        binders = self.binder_repo.list_active()

        for binder in binders:
            client = self.client_repo.get_by_id(binder.client_id)
            if not client:
                continue

            # Idle binder
            if WorkStateService.is_idle(binder, reference_date):
                items.append({
                    "item_type": "idle_binder",
                    "binder_id": binder.id,
                    "client_id": client.id,
                    "client_name": client.full_name,
                    "description": f"Binder {binder.binder_number} idle for {(reference_date - binder.received_at).days} days",
                })

            # Ready for pickup
            from app.models import BinderStatus
            if binder.status == BinderStatus.READY_FOR_PICKUP:
                items.append({
                    "item_type": "ready_for_pickup",
                    "binder_id": binder.id,
                    "client_id": client.id,
                    "client_name": client.full_name,
                    "description": f"Binder {binder.binder_number} ready for pickup",
                })

        return items