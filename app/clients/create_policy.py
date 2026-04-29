from datetime import date
from decimal import Decimal
from typing import Optional

from app.common.enums import EntityType, IdNumberType, VatType
from app.core.api_types import ApiDecimal
from tax_rules import get_financial


def derive_id_number_type(entity_type: EntityType) -> IdNumberType:
    if entity_type == EntityType.COMPANY_LTD:
        return IdNumberType.CORPORATION
    if entity_type in {EntityType.OSEK_PATUR, EntityType.OSEK_MURSHE}:
        return IdNumberType.INDIVIDUAL
    raise ValueError("סוג ישות זה אינו נתמך בפתיחת לקוח")


def normalize_vat_reporting_frequency(
    entity_type: Optional[EntityType],
    vat_reporting_frequency: Optional[VatType],
) -> Optional[VatType]:
    if entity_type == EntityType.OSEK_PATUR:
        return VatType.EXEMPT
    return vat_reporting_frequency


def normalize_vat_exempt_ceiling(entity_type: Optional[EntityType]) -> Optional[ApiDecimal]:
    if entity_type == EntityType.OSEK_PATUR:
        year = date.today().year
        return Decimal(str(get_financial(year, "osek_patur_ceiling_ils").value))
    return None


def preview_vat_reporting_frequency(
    entity_type: Optional[EntityType],
    vat_reporting_frequency: Optional[VatType],
) -> Optional[VatType]:
    if entity_type == EntityType.OSEK_PATUR:
        return None
    return vat_reporting_frequency
