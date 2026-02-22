from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import BinderStatus
from app.charge.models.charge import ChargeStatus
from app.users.models.user import UserRole
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository
from app.dashboard.services.dashboard_extended_builders import (
    idle_attention_item,
    ready_attention_item,
    unpaid_charge_attention_item,
    work_queue_item,
)
from app.binders.services.signals_service import SignalsService
from app.binders.services.work_state_service import WorkStateService
from app.clients.models.client import Client


class DashboardExtendedService:
    """Dashboard extensions for operational UX."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_repo = ClientRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.signals_service = SignalsService(db)
        self._cached_active_binders_with_clients: Optional[list[tuple]] = None

    def _active_binders_with_clients(self) -> list[tuple]:
        """Fetch active binders once and attach client objects to avoid N+1."""
        if self._cached_active_binders_with_clients is None:
            binders = self.binder_repo.list_active()
            client_ids = {binder.client_id for binder in binders}
            clients = (
                self.db.query(Client)
                .filter(Client.id.in_(client_ids))
                .all()
                if client_ids
                else []
            )
            client_map = {client.id: client for client in clients}
            self._cached_active_binders_with_clients = [
                (binder, client_map.get(binder.client_id))
                for binder in binders
                if client_map.get(binder.client_id)
            ]
        return self._cached_active_binders_with_clients

    def get_work_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[dict], int]:
        if reference_date is None:
            reference_date = date.today()

        items = []
        for binder, client in self._active_binders_with_clients():
            work_state = WorkStateService.derive_work_state(binder, reference_date, self.db)
            signals = self.signals_service.compute_binder_signals(binder, reference_date)
            items.append(work_queue_item(binder, client, work_state, signals, reference_date))
        total = len(items)
        offset = (page - 1) * page_size
        return items[offset : offset + page_size], total

    def get_attention_items(
        self,
        user_role: Optional[UserRole] = None,
        reference_date: Optional[date] = None,
    ) -> list[dict]:
        if reference_date is None:
            reference_date = date.today()

        items = []
        for binder, client in self._active_binders_with_clients():
            if WorkStateService.is_idle(binder, reference_date, self.db):
                items.append(idle_attention_item(binder, client, reference_date))
            if binder.status == BinderStatus.READY_FOR_PICKUP:
                items.append(ready_attention_item(binder, client))

        if user_role == UserRole.ADVISOR:
            unpaid_charges = self.charge_repo.list_charges(
                status=ChargeStatus.ISSUED.value,
                page=1,
                page_size=1000,
            )
            if unpaid_charges:
                charge_client_ids = {c.client_id for c in unpaid_charges}
                charge_clients = (
                    self.db.query(Client)
                    .filter(Client.id.in_(charge_client_ids))
                    .all()
                )
                charge_client_map = {c.id: c for c in charge_clients}
                for charge in unpaid_charges:
                    client = charge_client_map.get(charge.client_id)
                    if not client:
                        continue
                    items.append(unpaid_charge_attention_item(charge, client))

        return items
