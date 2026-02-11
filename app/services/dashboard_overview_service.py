from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ChargeStatus, ClientStatus, UserRole
from app.repositories import (
    BinderRepository,
    ChargeRepository,
    ClientRepository,
    DashboardOverviewRepository,
)
from app.services.action_contracts import build_action, get_binder_actions


class DashboardOverviewService:
    """Sprint 2 dashboard overview business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardOverviewRepository(db)
        self.binder_repo = BinderRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.client_repo = ClientRepository(db)

    def _build_quick_actions(self, user_role: Optional[UserRole]) -> list[dict]:
        actions: list[dict] = []

        binders = self.binder_repo.list_active()

        ready_candidate = next(
            (binder for binder in binders if "ready" in get_binder_actions(binder)),
            None,
        )
        if ready_candidate is not None:
            actions.append(
                build_action(
                    key="ready",
                    label="מוכן לאיסוף",
                    method="post",
                    endpoint=f"/binders/{ready_candidate.id}/ready",
                )
            )

        return_candidate = next(
            (binder for binder in binders if "return" in get_binder_actions(binder)),
            None,
        )
        if return_candidate is not None:
            actions.append(
                build_action(
                    key="return",
                    label="החזרת תיק",
                    method="post",
                    endpoint=f"/binders/{return_candidate.id}/return",
                    confirm_required=True,
                    confirm_title="אישור החזרת תיק",
                    confirm_message="האם לאשר החזרת תיק ללקוח?",
                    confirm_label="אישור",
                    cancel_label="ביטול",
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
                        confirm_required=True,
                        confirm_title="אישור הקפאת לקוח",
                        confirm_message="האם להקפיא את הלקוח?",
                        confirm_label="הקפאה",
                        cancel_label="ביטול",
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
        return overview
