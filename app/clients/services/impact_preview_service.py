from datetime import date
from typing import Optional

from app.actions.obligation_orchestrator import _years_to_generate
from app.common.enums import EntityType, VatType
from app.clients.schemas.impact import CreationImpactItem, ClientCreationImpactResponse

_VAT_DEADLINES_PER_YEAR = {VatType.MONTHLY: 12, VatType.BIMONTHLY: 6, VatType.EXEMPT: 0}
_ADVANCE_DEADLINES_PER_YEAR = 12


def compute_creation_impact(
    entity_type: Optional[EntityType],
    vat_reporting_frequency: Optional[VatType],
    reference_date: Optional[date] = None,
) -> ClientCreationImpactResponse:
    if entity_type == EntityType.EMPLOYEE:
        raise ValueError("פתיחת לקוח מסוג שכיר אינה נתמכת במערכת")

    years = _years_to_generate(reference_date)
    n = len(years)
    is_exempt = vat_reporting_frequency in (VatType.EXEMPT, None)
    vat_per_year = _VAT_DEADLINES_PER_YEAR.get(vat_reporting_frequency, 0)

    vat_count = vat_per_year * n
    advance_count = 0 if is_exempt else _ADVANCE_DEADLINES_PER_YEAR * n
    annual_deadline_count = n
    reminder_count = vat_count + advance_count + annual_deadline_count

    items = [
        CreationImpactItem(label="קלסר פעיל", count=1),
        CreationImpactItem(label='מועדי מע"מ', count=vat_count),
        CreationImpactItem(label="מועדי מקדמות", count=advance_count),
        CreationImpactItem(label="מועדי דוח שנתי", count=annual_deadline_count),
        CreationImpactItem(label="תזכורות", count=reminder_count),
        CreationImpactItem(label="דוחות שנתיים", count=n),
    ]
    items = [i for i in items if i.count > 0]

    note = 'פטור ממע"מ — לא ייווצרו מועדי מע"מ ומקדמות' if is_exempt else None

    return ClientCreationImpactResponse(items=items, years_scope=n, note=note)
