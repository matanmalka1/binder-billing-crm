from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.charge.models.charge import ChargeStatus
from app.clients.models.client import ClientStatus
from app.users.models.user import UserRole
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository
from app.dashboard.repositories.dashboard_overview_repository import DashboardOverviewRepository
from app.actions.action_contracts import get_binder_actions, get_charge_actions, get_client_actions
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService


class DashboardOverviewService:
    """ dashboard overview business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardOverviewRepository(db)
        self.binder_repo = BinderRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.client_repo = ClientRepository(db)
        self.extended_service = DashboardExtendedService(db)

    def _build_quick_actions(self, user_role: Optional[UserRole]) -> list[dict]:
        actions: list[dict] = []

        binders = self.binder_repo.list_active()

        ready_candidate = None
        return_candidate = None
        for binder in binders:
            binder_actions = get_binder_actions(binder)
            if ready_candidate is None and any(a["key"] == "ready" for a in binder_actions):
                ready_candidate = (binder, next(a for a in binder_actions if a["key"] == "ready"))
            if return_candidate is None and any(a["key"] == "return" for a in binder_actions):
                return_candidate = (binder, next(a for a in binder_actions if a["key"] == "return"))
            if ready_candidate and return_candidate:
                break

        if ready_candidate is not None:
            binder, action = ready_candidate
            client = self.client_repo.get_by_id(binder.client_id)
            action["client_name"] = client.full_name if client else None
            action["binder_number"] = binder.binder_number
            actions.append(action)

        if return_candidate is not None:
            binder, action = return_candidate
            client = self.client_repo.get_by_id(binder.client_id)
            action["client_name"] = client.full_name if client else None
            action["binder_number"] = binder.binder_number
            actions.append(action)

        if user_role == UserRole.ADVISOR:
            issued_charges = self.charge_repo.list_charges(
                status=ChargeStatus.ISSUED.value,
                page=1,
                page_size=1,
            )
            if issued_charges:
                charge = issued_charges[0]
                charge_actions = get_charge_actions(charge)
                mark_paid = next((a for a in charge_actions if a["key"] == "mark_paid"), None)
                if mark_paid:
                    charge_client = self.client_repo.get_by_id(charge.client_id) if charge.client_id else None
                    mark_paid["client_name"] = charge_client.full_name if charge_client else None
                    actions.append(mark_paid)

            active_clients = self.client_repo.list(
                status=ClientStatus.ACTIVE.value,
                page=1,
                page_size=1,
            )
            if active_clients:
                client = active_clients[0]
                client_actions = get_client_actions(client, user_role)
                freeze = next((a for a in client_actions if a["key"] == "freeze"), None)
                if freeze:
                    freeze["client_name"] = client.full_name
                    actions.append(freeze)

        frozen_clients = self.client_repo.list(
            status=ClientStatus.FROZEN.value,
            page=1,
            page_size=1,
        )
        if frozen_clients:
            client = frozen_clients[0]
            client_actions = get_client_actions(client, user_role)
            activate = next((a for a in client_actions if a["key"] == "activate"), None)
            if activate:
                activate["client_name"] = client.full_name
                actions.append(activate)

        return actions

    def get_overview(
        self,
        reference_date: Optional[date] = None,
        user_role: Optional[UserRole] = None,
    ) -> dict:
        """
        Get dashboard overview metrics.

        Returns:
            {
                "total_clients": int,
                "active_binders": int,
            }
        """
        if reference_date is None:
            reference_date = date.today()

        overview = self.repo.get_overview_metrics(reference_date)
        overview["work_state"] = None
        overview["signals"] = []
        overview["quick_actions"] = self._build_quick_actions(user_role)
        attention_items = self.extended_service.get_attention_items(user_role=user_role)
        overview["attention"] = {"items": attention_items, "total": len(attention_items)}
        return overview
