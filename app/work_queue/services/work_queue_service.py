from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.utils.time_utils import israel_today
from app.work_queue.schemas.work_queue import WorkQueueItem, WorkQueueSourceType
from app.work_queue.services.billing_items import (
    advance_payment_items,
    unpaid_charge_items,
)
from app.work_queue.services.binder_items import stale_binder_items
from app.work_queue.services.common import WorkQueueContext
from app.work_queue.services.task_items import task_items
from app.work_queue.services.tax_items import annual_report_items, vat_filing_items

_FAR_FUTURE = date(9999, 12, 31)


class WorkQueueService:
    def __init__(self, db: Session):
        self.ctx = WorkQueueContext(db, israel_today())

    def list_items(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
        exclude_source_types: Optional[List[WorkQueueSourceType]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkQueueItem]:
        excluded = set(exclude_source_types or [])
        items: List[WorkQueueItem] = []

        # VAT, annual reports, and advance payments are client-level obligations —
        # business_id does not narrow them; skip entirely when business_id is set.
        if business_id is None:
            if WorkQueueSourceType.VAT_FILING not in excluded:
                items.extend(vat_filing_items(self.ctx, client_record_id))
            if WorkQueueSourceType.ANNUAL_REPORT not in excluded:
                items.extend(annual_report_items(self.ctx, client_record_id))
            if WorkQueueSourceType.ADVANCE_PAYMENT not in excluded:
                items.extend(advance_payment_items(self.ctx, client_record_id))

        if WorkQueueSourceType.UNPAID_CHARGE not in excluded:
            items.extend(unpaid_charge_items(self.ctx, client_record_id, business_id))

        # Tasks and stale binders are not client-scoped; include when no client filter is active
        if client_record_id is None and business_id is None:
            if WorkQueueSourceType.TASK not in excluded:
                items.extend(task_items(self.ctx))
            if WorkQueueSourceType.STALE_BINDER not in excluded:
                items.extend(stale_binder_items(self.ctx))

        # Sort: dated items first by due_date, null due_date items last
        items.sort(
            key=lambda item: item.due_date if item.due_date is not None else _FAR_FUTURE
        )
        return items[offset : offset + limit]
