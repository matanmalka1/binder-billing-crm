"""Service: client-level VAT summary."""

from app.clients.repositories.client_repository import ClientRepository
from app.vat_reports.repositories.vat_client_summary_repository import (
    VatClientSummaryRepository,
)
from app.vat_reports.schemas.vat_client_summary_schema import VatClientSummaryResponse


def get_client_summary(
    summary_repo: VatClientSummaryRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
) -> VatClientSummaryResponse:
    client = client_repo.get_by_id(client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    periods = summary_repo.get_periods_for_client(client_id)
    annual = summary_repo.get_annual_aggregates(client_id)

    return VatClientSummaryResponse(
        client_id=client_id,
        periods=periods,
        annual=annual,
    )
