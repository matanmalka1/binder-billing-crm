"""Resolves the effective VAT reporting frequency for a business."""

from typing import Optional

from app.businesses.models.business import BusinessType
from app.businesses.models.business_tax_profile import VatType
from app.clients.repositories.client_repository import ClientRepository


def resolve_effective_vat_type(business, profile, client_repo: Optional[ClientRepository]) -> VatType:
    """
    Determine the effective VAT reporting frequency for a business.

    - COMPANY: uses BusinessTaxProfile.vat_type (independent legal entity, own ח"פ)
    - OSEK_MURSHE: uses Client.vat_reporting_frequency (shared across all businesses under the client)
      Falls back to BIMONTHLY if Client.vat_reporting_frequency is not yet configured (NULL).
    - OSEK_PATUR / EMPLOYEE: returns EXEMPT — assert_business_allows_create blocks work item
      creation before this is reached; this is a safety-net fallback.
    """
    if business.business_type == BusinessType.COMPANY:
        return profile.vat_type if (profile and profile.vat_type) else VatType.MONTHLY
    if business.business_type == BusinessType.OSEK_MURSHE:
        client = client_repo.get_by_id(business.client_id) if client_repo else None
        freq = client.vat_reporting_frequency if (client and client.vat_reporting_frequency) else None
        return freq or VatType.BIMONTHLY
    return VatType.EXEMPT
