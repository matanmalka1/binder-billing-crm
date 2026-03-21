"""Schemas for income/expense lines and financial summary."""

from decimal import Decimal
from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType


# ── Income ────────────────────────────────────────────────────────────────────

class IncomeLineCreateRequest(BaseModel):
    source_type: IncomeSourceType           # enum — לא str חופשי
    amount: Decimal = Field(gt=0)
    description: Optional[str] = None


class IncomeLineUpdateRequest(BaseModel):
    source_type: Optional[IncomeSourceType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None


class IncomeLineResponse(BaseModel):
    id: int
    annual_report_id: int
    source_type: IncomeSourceType
    amount: Decimal
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Expenses ──────────────────────────────────────────────────────────────────

class ExpenseLineCreateRequest(BaseModel):
    category: ExpenseCategoryType           # enum — לא str חופשי
    amount: Decimal = Field(gt=0)
    description: Optional[str] = None
    recognition_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    supporting_document_ref: Optional[str] = None
    supporting_document_id: Optional[int] = None


class ExpenseLineUpdateRequest(BaseModel):
    category: Optional[ExpenseCategoryType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    recognition_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    supporting_document_ref: Optional[str] = None
    supporting_document_id: Optional[int] = None


class ExpenseLineResponse(BaseModel):
    id: int
    annual_report_id: int
    category: ExpenseCategoryType
    amount: Decimal
    recognition_rate: Decimal
    recognized_amount: Decimal = Decimal("0")
    supporting_document_ref: Optional[str] = None
    supporting_document_id: Optional[int] = None
    supporting_document_filename: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        instance = super().model_validate(obj, *args, **kwargs)
        if hasattr(obj, "supporting_document") and obj.supporting_document is not None:
            key = obj.supporting_document.storage_key or ""
            object.__setattr__(instance, "supporting_document_filename", key.split("/")[-1])
        return instance

    def model_post_init(self, __context) -> None:
        object.__setattr__(
            self, "recognized_amount",
            (self.amount * self.recognition_rate).quantize(Decimal("0.01"))
        )


# ── Financial summary ─────────────────────────────────────────────────────────

class FinancialSummaryResponse(BaseModel):
    annual_report_id: int
    total_income: Decimal
    gross_expenses: Decimal
    recognized_expenses: Decimal
    taxable_income: Decimal
    income_lines: list[IncomeLineResponse] = []
    expense_lines: list[ExpenseLineResponse] = []


# ── Tax calculation ───────────────────────────────────────────────────────────

class BracketBreakdownItem(BaseModel):
    rate: float
    from_amount: Decimal
    to_amount: Optional[Decimal] = None
    taxable_in_bracket: Decimal
    tax_in_bracket: Decimal


class NationalInsuranceResponse(BaseModel):
    base_amount: Decimal
    high_amount: Decimal
    total: Decimal


class TaxCalculationResponse(BaseModel):
    taxable_income: Decimal
    pension_deduction: Decimal
    tax_before_credits: Decimal
    credit_points_value: Decimal
    donation_credit: Decimal
    other_credits: Decimal
    tax_after_credits: Decimal
    net_profit: Decimal
    effective_rate: float
    national_insurance: NationalInsuranceResponse
    brackets: list[BracketBreakdownItem]
    total_liability: Optional[Decimal] = None
    total_credit_points: float = 0.0


# ── Advances summary ──────────────────────────────────────────────────────────

class AdvancesSummary(BaseModel):
    total_advances_paid: Decimal
    advances_count: int
    final_balance: Decimal
    balance_type: Literal["due", "refund", "zero"]


# ── Readiness check ───────────────────────────────────────────────────────────

class ReadinessCheckResponse(BaseModel):
    annual_report_id: int
    is_ready: bool
    issues: list[str]
    completion_pct: float   # 0.0–100.0, rounded to 1 decimal