"""Orchestrates urgency-sorted quick actions for the Advisor dashboard panel."""

from __future__ import annotations

from typing import Optional

from app.actions.action_contracts import get_charge_actions
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.models.charge import ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository
from app.users.models.user import UserRole
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.dashboard.services._quick_actions_helpers import (
    CATEGORY_ORDER,
    build_annual_report_actions,
    build_binder_actions,
    build_vat_actions,
    enrich,
)


def build_quick_actions(
    binder_repo: BinderRepository,
    charge_repo: ChargeRepository,
    client_repo: ClientRepository,
    vat_repo: VatWorkItemRepository,
    annual_report_repo: AnnualReportRepository,
    user_role: Optional[UserRole],
    current_period: str,
) -> list[dict]:
    actions: list[dict] = []

    actions.extend(build_binder_actions(binder_repo, client_repo))
    actions.extend(build_vat_actions(vat_repo, client_repo, current_period))
    actions.extend(build_annual_report_actions(annual_report_repo, client_repo))

    if user_role == UserRole.ADVISOR:
        issued = charge_repo.list_charges(status=ChargeStatus.ISSUED.value, page=1, page_size=1)
        if issued:
            charge = issued[0]
            charge_acts = get_charge_actions(charge)
            mark_paid = next((a for a in charge_acts if a["key"] == "mark_paid"), None)
            if mark_paid:
                c = client_repo.get_by_id(charge.client_id) if charge.client_id else None
                mark_paid["client_name"] = c.full_name if c else None
                enrich(mark_paid, "charges")
                actions.append(mark_paid)

    actions.sort(key=lambda a: CATEGORY_ORDER.get(a.get("category", "clients"), 99))
    return actions
