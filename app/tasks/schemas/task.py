from __future__ import annotations

from datetime import date
from enum import Enum as PyEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel


class TaskType(str, PyEnum):
    VAT_FILING = "vat_filing"
    ANNUAL_REPORT = "annual_report"
    ADVANCE_PAYMENT = "advance_payment"
    UNPAID_CHARGE = "unpaid_charge"


class TaskUrgency(str, PyEnum):
    OVERDUE = "overdue"
    APPROACHING = "approaching"  # <= 7 days
    UPCOMING = "upcoming"  # 8-14 days


class DeadlineTask(BaseModel):
    item_type: Literal["task"] = "task"
    source_type: TaskType
    source_id: int
    label: str
    due_date: date
    urgency: TaskUrgency
    client_record_id: int
    client_name: Optional[str] = None
    business_id: Optional[int] = None
    payload: Optional[dict[str, Any]] = None


class UnifiedItem(BaseModel):
    item_type: Literal["task", "reminder"]
    source_type: str
    source_id: int
    label: str
    due_date: date
    urgency: Optional[str] = None
    client_record_id: Optional[int] = None
    client_name: Optional[str] = None
    business_id: Optional[int] = None
    payload: Optional[dict[str, Any]] = None
