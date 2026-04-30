from typing import Literal, Optional
import re

from pydantic import BaseModel, Field, field_validator

from app.charge.models.charge import ChargeType, ChargeStatus
from app.charge.services.constants import MONTHS_COVERED_MAX, PERIOD_REGEX
from app.charge.services.messages import PERIOD_INVALID_FORMAT
from app.core.api_types import ApiDateTime, ApiDecimal


class ChargeCreateRequest(BaseModel):
    client_record_id: int
    business_id: Optional[int] = None
    amount: ApiDecimal = Field(gt=0)
    charge_type: ChargeType                                              # enum — לא str חופשי
    period: Optional[str] = None                                        # "YYYY-MM"
    months_covered: int = Field(1, ge=1, le=MONTHS_COVERED_MAX)        # monthly or bimonthly

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.fullmatch(PERIOD_REGEX, v):
            raise ValueError(PERIOD_INVALID_FORMAT)
        return v


class ChargeResponse(BaseModel):
    id: int
    client_record_id: int
    office_client_number: Optional[int] = None
    business_id: Optional[int] = None
    business_name: Optional[str] = None        # enriched by service
    annual_report_id: Optional[int] = None
    charge_type: ChargeType
    status: ChargeStatus
    amount: ApiDecimal
    period: Optional[str] = None
    months_covered: int
    description: Optional[str] = None
    created_at: ApiDateTime
    created_by: Optional[int] = None
    issued_at: Optional[ApiDateTime] = None
    issued_by: Optional[int] = None
    paid_at: Optional[ApiDateTime] = None
    paid_by: Optional[int] = None
    canceled_at: Optional[ApiDateTime] = None
    canceled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    available_actions: list[dict] = []

    model_config = {"from_attributes": True}


class ChargeResponseSecretary(BaseModel):
    """תגובה מצומצמת לסקרטרית — ללא נתונים פיננסיים."""
    id: int
    client_record_id: int
    office_client_number: Optional[int] = None
    business_id: Optional[int] = None
    business_name: Optional[str] = None
    charge_type: ChargeType
    status: ChargeStatus
    period: Optional[str] = None
    months_covered: int
    description: Optional[str] = None
    created_at: ApiDateTime
    issued_at: Optional[ApiDateTime] = None
    paid_at: Optional[ApiDateTime] = None
    available_actions: list[dict] = []

    model_config = {"from_attributes": True}


class ChargeCancelRequest(BaseModel):
    reason: Optional[str] = None


class ChargeStatusStat(BaseModel):
    count: int = 0
    amount: ApiDecimal = ApiDecimal("0")


class ChargeListStats(BaseModel):
    draft: ChargeStatusStat = ChargeStatusStat()
    issued: ChargeStatusStat = ChargeStatusStat()
    paid: ChargeStatusStat = ChargeStatusStat()
    canceled: ChargeStatusStat = ChargeStatusStat()


class ChargeListResponse(BaseModel):
    items: list[ChargeResponse | ChargeResponseSecretary]
    page: int
    page_size: int
    total: int
    stats: ChargeListStats


class BulkChargeActionRequest(BaseModel):
    charge_ids: list[int] = Field(min_length=1)
    action: Literal["issue", "mark-paid", "cancel"]
    cancellation_reason: Optional[str] = None


class BulkChargeFailedItem(BaseModel):
    id: int
    error: str


class BulkChargeActionResponse(BaseModel):
    succeeded: list[int]
    failed: list[BulkChargeFailedItem]
