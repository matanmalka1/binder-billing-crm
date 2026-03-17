from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.vat_reports.models.vat_enums import VatWorkItemStatus


class VatPeriodRow(BaseModel):
    work_item_id: int
    period: str
    status: VatWorkItemStatus
    total_output_vat: Decimal
    total_input_vat: Decimal
    net_vat: Decimal
    total_output_net: Decimal
    total_input_net: Decimal
    final_vat_amount: Optional[Decimal]
    filed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class VatAnnualSummary(BaseModel):
    year: int
    total_output_vat: Decimal
    total_input_vat: Decimal
    net_vat: Decimal
    periods_count: int
    filed_count: int


class VatClientSummaryResponse(BaseModel):
    client_id: int
    periods: list[VatPeriodRow]
    annual: list[VatAnnualSummary]
