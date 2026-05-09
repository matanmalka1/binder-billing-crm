from __future__ import annotations

from datetime import date
from enum import Enum as PyEnum
from typing import Any, Optional

from pydantic import BaseModel


class WorkQueueSourceType(str, PyEnum):
    VAT_FILING = "vat_filing"
    ANNUAL_REPORT = "annual_report"
    ADVANCE_PAYMENT = "advance_payment"
    UNPAID_CHARGE = "unpaid_charge"
    TASK = "task"


class WorkQueueUrgency(str, PyEnum):
    OVERDUE = "overdue"
    APPROACHING = "approaching"
    UPCOMING = "upcoming"


class WorkQueueItem(BaseModel):
    source_type: WorkQueueSourceType
    source_id: int
    label: str
    due_date: Optional[date] = None
    urgency: WorkQueueUrgency
    client_record_id: Optional[int] = None
    client_name: Optional[str] = None
    business_id: Optional[int] = None
    payload: Optional[dict[str, Any]] = None
