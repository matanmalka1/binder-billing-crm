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
from app.actions.action_contracts import build_action, get_binder_actions
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService


class DashboardOverviewService:
    """Sprint 2 dashboard overview business logic."""

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
            if ready_candidate is None and any(action["key"] == "ready" for action in binder_actions):
                ready_candidate = binder
            if return_candidate is None and any(action["key"] == "return" for action in binder_actions):
                return_candidate = binder
            if ready_candidate and return_candidate:
                break

        if ready_candidate is not None:
            actions.append(
                build_action(
                    key="ready",
                    label="מוכן לאיסוף",
                    method="post",
                    endpoint=f"/binders/{ready_candidate.id}/ready",
                    action_id=f"binder-{ready_candidate.id}-ready",
                )
            )

        if return_candidate is not None:
            actions.append(
                build_action(
                    key="return",
                    label="החזרת קלסר",
                    method="post",
                    endpoint=f"/binders/{return_candidate.id}/return",
                    action_id=f"binder-{return_candidate.id}-return",
                    confirm={
                        "title": "אישור החזרת קלסר",
                        "message": "האם לאשר החזרת קלסר ללקוח?",
                        "confirm_label": "אישור",
                        "cancel_label": "ביטול",
                    },
                )
            )

        if user_role == UserRole.ADVISOR:
            issued_charges = self.charge_repo.list_charges(
                status=ChargeStatus.ISSUED.value,
                page=1,
                page_size=1,
            )
            if issued_charges:
                charge = issued_charges[0]
                actions.append(
                    build_action(
                        key="mark_paid",
                        label="סימון חיוב כשולם",
                        method="post",
                        endpoint=f"/charges/{charge.id}/mark-paid",
                        action_id=f"charge-{charge.id}-mark_paid",
                    )
                )

            active_clients = self.client_repo.list(
                status=ClientStatus.ACTIVE.value,
                page=1,
                page_size=1,
            )
            if active_clients:
                client = active_clients[0]
                actions.append(
                    build_action(
                        key="freeze",
                        label="הקפאת לקוח",
                        method="patch",
                        endpoint=f"/clients/{client.id}",
                        payload={"status": "frozen"},
                        action_id=f"client-{client.id}-freeze",
                        confirm={
                            "title": "אישור הקפאת לקוח",
                            "message": "האם להקפיא את הלקוח?",
                            "confirm_label": "הקפאה",
                            "cancel_label": "ביטול",
                        },
                    )
                )

        frozen_clients = self.client_repo.list(
            status=ClientStatus.FROZEN.value,
            page=1,
            page_size=1,
        )
        if frozen_clients:
            client = frozen_clients[0]
            actions.append(
                build_action(
                    key="activate",
                    label="הפעלת לקוח",
                    method="patch",
                    endpoint=f"/clients/{client.id}",
                    payload={"status": "active"},
                    action_id=f"client-{client.id}-activate",
                )
            )

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
                "overdue_binders": int,
                "binders_due_today": int,
                "binders_due_this_week": int
            }
        """
        if reference_date is None:
            reference_date = date.today()

        overview = self.repo.get_overview_metrics(reference_date)
        overview["work_state"] = None
        overview["sla_state"] = None
        overview["signals"] = []
        overview["quick_actions"] = self._build_quick_actions(user_role)
        attention_items = self.extended_service.get_attention_items(user_role=user_role)
        overview["attention"] = {"items": attention_items, "total": len(attention_items)}
        return overview
