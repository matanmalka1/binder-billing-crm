from decimal import Decimal

from pydantic import BaseModel


class TaxSubmissionWidgetResponse(BaseModel):
    tax_year: int
    total_clients: int
    reports_submitted: int
    reports_in_progress: int
    reports_not_started: int
    submission_percentage: float
    total_refund_due: Decimal
    total_tax_due: Decimal