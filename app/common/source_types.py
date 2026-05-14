from __future__ import annotations

from enum import Enum as PyEnum


class WorkQueueSourceType(str, PyEnum):
    VAT_WORK_ITEM = "vat_work_item"
    ANNUAL_REPORT = "annual_report"
    ADVANCE_PAYMENT = "advance_payment"
    CHARGE = "charge"
    BINDER = "binder"
    TASK = "task"


def normalize_source_domain(value: str | None) -> WorkQueueSourceType | None:
    if not value:
        return None
    try:
        return WorkQueueSourceType(value)
    except ValueError:
        return None


def source_route(source_type: WorkQueueSourceType, source_id: int) -> str | None:
    if source_type == WorkQueueSourceType.VAT_WORK_ITEM:
        return f"/tax/vat/{source_id}"
    if source_type == WorkQueueSourceType.ANNUAL_REPORT:
        return f"/tax/reports/{source_id}"
    if source_type == WorkQueueSourceType.ADVANCE_PAYMENT:
        return "/tax/advance-payments"
    if source_type == WorkQueueSourceType.CHARGE:
        return f"/charges?charge_id={source_id}"
    if source_type == WorkQueueSourceType.BINDER:
        return f"/binders?binder_id={source_id}"
    return None


__all__ = ["WorkQueueSourceType", "normalize_source_domain", "source_route"]
