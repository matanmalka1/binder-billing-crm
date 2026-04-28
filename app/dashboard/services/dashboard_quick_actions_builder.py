"""Orchestrates urgency-sorted quick actions for the Advisor dashboard panel."""

from __future__ import annotations

from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.dashboard.services._quick_actions_helpers import (
    CATEGORY_ORDER,
    build_annual_report_actions,
    build_binder_actions,
    build_vat_actions,
)


def build_quick_actions(
    binder_repo: BinderRepository,
    business_repo: BusinessRepository,
    vat_repo: VatWorkItemRepository,
    annual_report_repo: AnnualReportRepository,
    current_period: str,
) -> list[dict]:
    actions: list[dict] = []

    actions.extend(build_binder_actions(binder_repo, business_repo))
    actions.extend(build_vat_actions(vat_repo, business_repo, current_period))
    actions.extend(build_annual_report_actions(annual_report_repo, business_repo))

    actions.sort(key=lambda a: CATEGORY_ORDER.get(a.get("category", "clients"), 99))
    return actions
