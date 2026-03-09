"""Schemas for income/expense lines and financial summary."""

from decimal import Decimal
from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel


# ── Income ────────────────────────────────────────────────────────────────────

class IncomeLineCreateRequest(BaseModel):
    source_type: str   # IncomeSourceType value
    amount: Decimal
    description: Optional[str] = None


class IncomeLineUpdateRequest(BaseModel):
    source_type: Optional[str] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None


class IncomeLineResponse(BaseModel):
    id: int
    annual_report_id: int
    source_type: str
    amount: float
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Expenses ──────────────────────────────────────────────────────────────────

class ExpenseLineCreateRequest(BaseModel):
    category: str   # ExpenseCategoryType value
    amount: Decimal
    description: Optional[str] = None
    recognition_rate: Optional[Decimal] = None  # defaults to statutory rate for category


class ExpenseLineUpdateRequest(BaseModel):
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    recognition_rate: Optional[Decimal] = None


class ExpenseLineResponse(BaseModel):
    id: int
    annual_report_id: int
    category: str
    amount: float
    recognition_rate: float
    recognized_amount: float = 0.0
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    def model_post_init(self, __context) -> None:
        object.__setattr__(self, "recognized_amount", round(self.amount * self.recognition_rate, 2))


# ── Financial summary ─────────────────────────────────────────────────────────

class FinancialSummaryResponse(BaseModel):
    annual_report_id: int
    total_income: float
    gross_expenses: float
    recognized_expenses: float
    taxable_income: float
    income_lines: list[IncomeLineResponse] = []
    expense_lines: list[ExpenseLineResponse] = []


# ── Tax calculation ───────────────────────────────────────────────────────────

class BracketBreakdownItem(BaseModel):
    rate: float
    from_amount: float
    to_amount: float | None
    taxable_in_bracket: float
    tax_in_bracket: float


class NationalInsuranceResponse(BaseModel):
    base_amount: float
    high_amount: float
    total: float


class TaxCalculationResponse(BaseModel):
    taxable_income: float
    pension_deduction: float
    tax_before_credits: float
    credit_points_value: float
    donation_credit: float
    other_credits: float
    tax_after_credits: float
    effective_rate: float
    national_insurance: NationalInsuranceResponse
    brackets: list[BracketBreakdownItem]


# ── Advances summary ──────────────────────────────────────────────────────────

class AdvancesSummary(BaseModel):
    total_advances_paid: float
    advances_count: int
    final_balance: float
    balance_type: Literal["due", "refund", "zero"]


# ── Readiness check ───────────────────────────────────────────────────────────

class ReadinessCheckResponse(BaseModel):
    annual_report_id: int
    is_ready: bool
    issues: list[str]
    completion_pct: float  # 0.0–100.0, rounded to 1 decimal
