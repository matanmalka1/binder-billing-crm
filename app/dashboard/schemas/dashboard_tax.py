from decimal import Decimal

from pydantic import BaseModel

from app.core.api_types import ApiDecimal


class TaxSubmissionWidgetResponse(BaseModel):
    tax_year: int
    total_clients: int
    reports_submitted: int
    reports_in_progress: int
    reports_not_started: int
    submission_percentage: float
    total_refund_due: ApiDecimal
    total_tax_due: ApiDecimal
