"""Schemas for the grouped deadline read model."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.tax_deadline.models.tax_deadline import DeadlineType, UrgencyLevel


class DeadlineGroupKey(BaseModel):
    deadline_type: str
    due_date: date


class DeadlineGroupPeriod(BaseModel):
    period: str
    period_months_count: Optional[int] = None


class DeadlineGroup(BaseModel):
    group_key: str
    deadline_type: DeadlineType
    period: Optional[str] = None
    period_months_count: Optional[int] = None
    tax_year: Optional[int] = None
    periods: list[DeadlineGroupPeriod] = Field(default_factory=list)
    tax_years: list[int] = Field(default_factory=list)
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
