"""Schemas for income/expense lines, financial summary, and tax calculation."""

from decimal import Decimal
from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.core.api_types import ApiDateTime, ApiDecimal


# ── Income ────────────────────────────────────────────────────────────────────

class IncomeLineCreateRequest(BaseModel):
    source_type: IncomeSourceType           # enum — לא str חופשי
    amount: ApiDecimal = Field(gt=0)
    description: Optional[str] = None


class IncomeLineUpdateRequest(BaseModel):
    source_type: Optional[IncomeSourceType] = None
    amount: Optional[ApiDecimal] = Field(None, gt=0)
    description: Optional[str] = None


class IncomeLineResponse(BaseModel):
    id: int
    annual_report_id: int
    source_type: IncomeSourceType
    amount: ApiDecimal
    description: Optional[str] = None
    created_at: ApiDateTime
    updated_at: Optional[ApiDateTime] = None

    model_config = {"from_attributes": True}


# ── Expenses ──────────────────────────────────────────────────────────────────

class ExpenseLineCreateRequest(BaseModel):
    category: ExpenseCategoryType           # enum — לא str חופשי
    amount: ApiDecimal = Field(gt=0)
    description: Optional[str] = None
    recognition_rate: Optional[ApiDecimal] = Field(None, ge=0, le=1)
    supporting_document_ref: Optional[str] = None
    supporting_document_id: Optional[int] = None


class ExpenseLineUpdateRequest(BaseModel):
    category: Optional[ExpenseCategoryType] = None
    amount: Optional[ApiDecimal] = Field(None, gt=0)
    description: Optional[str] = None
    recognition_rate: Optional[ApiDecimal] = Field(None, ge=0, le=1)
    supporting_document_ref: Optional[str] = None
    supporting_document_id: Optional[int] = None


class ExpenseLineResponse(BaseModel):
    id: int
    annual_report_id: int
    category: ExpenseCategoryType
    amount: ApiDecimal
    recognition_rate: ApiDecimal
    recognized_amount: ApiDecimal = Decimal("0")
    supporting_document_ref: Optional[str] = None
    supporting_document_id: Optional[int] = None
    supporting_document_filename: Optional[str] = None
    description: Optional[str] = None
    created_at: ApiDateTime
    updated_at: Optional[ApiDateTime] = None

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
    total_income: ApiDecimal
    gross_expenses: ApiDecimal
    recognized_expenses: ApiDecimal
    taxable_income: ApiDecimal
    income_lines: list[IncomeLineResponse] = []
    expense_lines: list[ExpenseLineResponse] = []


# ── Tax calculation ───────────────────────────────────────────────────────────

class BracketBreakdownItem(BaseModel):
    rate: float
    from_amount: ApiDecimal
    to_amount: Optional[ApiDecimal] = None
    taxable_in_bracket: ApiDecimal
    tax_in_bracket: ApiDecimal


class NationalInsuranceResponse(BaseModel):
    base_amount: ApiDecimal
    high_amount: ApiDecimal
    total: ApiDecimal


class TaxCalculationResponse(BaseModel):
    taxable_income: ApiDecimal
    pension_deduction: ApiDecimal
    tax_before_credits: ApiDecimal
    credit_points_value: ApiDecimal
    donation_credit: ApiDecimal
    other_credits: ApiDecimal
    tax_after_credits: ApiDecimal
    net_profit: ApiDecimal
    effective_rate: float
    national_insurance: NationalInsuranceResponse
    brackets: list[BracketBreakdownItem]
    total_liability: Optional[ApiDecimal] = None
    total_credit_points: float = 0.0


# ── Advances summary ──────────────────────────────────────────────────────────

class AdvancesSummary(BaseModel):
    total_advances_paid: ApiDecimal
    advances_count: int
    final_balance: ApiDecimal
    balance_type: Literal["due", "refund", "zero"]


# ── Readiness check ───────────────────────────────────────────────────────────

class ReadinessCheckResponse(BaseModel):
    annual_report_id: int
    is_ready: bool
    issues: list[str]
    completion_pct: float   # 0.0–100.0, rounded to 1 decimal


# ── Tax calculation save ──────────────────────────────────────────────────────

class TaxCalculationSaveRequest(BaseModel):
    tax_due: Optional[ApiDecimal] = None
    refund_due: Optional[ApiDecimal] = None


class TaxCalculationSaveResponse(BaseModel):
    annual_report_id: int
    tax_due: Optional[ApiDecimal]
    refund_due: Optional[ApiDecimal]
    saved_at: ApiDateTime


# ── VAT auto-populate ─────────────────────────────────────────────────────────

class VatAutoPopulateResponse(BaseModel):
    annual_report_id: int
    income_lines_created: int
    expense_lines_created: int
    income_total: ApiDecimal
    expense_total: ApiDecimal
    lines_deleted: int = 0
