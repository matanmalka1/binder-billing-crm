"""Schemas for the grouped deadline read model."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.tax_deadline.models.tax_deadline import DeadlineType, UrgencyLevel


class DeadlineGroupKey(BaseModel):
    deadline_type: str
    period: Optional[str] = None
    tax_year: Optional[int] = None
    due_date: date


class DeadlineGroup(BaseModel):
    group_key: str
    deadline_type: DeadlineType
    period: Optional[str] = None
    tax_year: Optional[int] = None
    due_date: date
    total_clients: int
    pending_count: int
    completed_count: int
    canceled_count: int
    overdue_count: int
    total_amount: Optional[Decimal] = None
    open_amount: Optional[Decimal] = None
    worst_urgency: UrgencyLevel


class GroupedDeadlineListResponse(BaseModel):
    groups: list[DeadlineGroup]
    total_groups: int
    total_client_deadlines: int
