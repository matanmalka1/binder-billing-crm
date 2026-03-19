"""Service: client-level VAT summary."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.businesses.repositories.business_repository import BusinessRepository
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository
from app.vat_reports.schemas.vat_client_summary_schema import (
    VatAnnualSummary,
    VatClientSummaryResponse,
    VatPeriodRow,
)


def get_business_summary(db: Session, *, business_id: int) -> VatClientSummaryResponse:
    summary_repo = VatClientSummaryRepository(db)
    business_repo = BusinessRepository(db)

    business = business_repo.get_by_id(business_id)
    if not business:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "VAT.NOT_FOUND")

    raw_periods = summary_repo.get_periods_for_business(business_id)
    periods = [
        VatPeriodRow(
            work_item_id=r.id,
            period=r.period,
            status=r.status,
            total_output_vat=r.total_output_vat,
            total_input_vat=r.total_input_vat,
            net_vat=r.net_vat,
            total_output_net=Decimal(str(output_net or 0)),
            total_input_net=Decimal(str(input_net or 0)),
            final_vat_amount=r.final_vat_amount,
            filed_at=r.filed_at,
        )
        for r, output_net, input_net in raw_periods
    ]

    raw_annual = summary_repo.get_annual_aggregates(business_id)
    annual = [VatAnnualSummary.model_validate(row) for row in raw_annual]

    return VatClientSummaryResponse(business_id=business_id, periods=periods, annual=annual)
