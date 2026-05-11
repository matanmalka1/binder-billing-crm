from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DeadlineRuleResponse(BaseModel):
    id: int
    rule_type: str
    due_day_of_month: int
    offset_months: int
    effective_from: date
    effective_to: date | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class TaxCalendarEntryResponse(BaseModel):
    id: int
    obligation_type: str
    period: str | None = None
    period_months_count: int | None = None
    tax_year: int
    due_date: date
    deadline_rule_id: int

    model_config = {"from_attributes": True}


class TaxCalendarSummaryResponse(BaseModel):
    start_year: int | None
    end_year: int | None
    total_entries: int
    per_year: dict[int, dict[str, int]]
    warnings: list[str]
