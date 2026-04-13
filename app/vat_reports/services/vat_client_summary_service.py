"""Service: client-level VAT summary."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.clients.repositories.client_repository import ClientRepository
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository
from app.vat_reports.schemas.vat_client_summary_schema import (
    VatAnnualSummary,
    VatClientSummaryResponse,
    VatPeriodRow,
)
from app.vat_reports.services.messages import VAT_CLIENT_NOT_FOUND


def get_client_summary(db: Session, *, client_id: int) -> VatClientSummaryResponse:
    summary_repo = VatClientSummaryRepository(db)
    client_repo = ClientRepository(db)

    client = client_repo.get_by_id(client_id)
    if not client:
        raise NotFoundError(VAT_CLIENT_NOT_FOUND.format(client_id=client_id), "VAT.NOT_FOUND")

    raw_periods = summary_repo.get_periods_for_client(client_id)
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

    raw_annual = summary_repo.get_annual_aggregates(client_id)
    annual = [VatAnnualSummary.model_validate(row) for row in raw_annual]

    return VatClientSummaryResponse(
        client_id=client_id,
        periods=periods,
        annual=annual,
    )
