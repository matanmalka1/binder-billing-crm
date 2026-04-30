from datetime import date
from typing import Optional

from app.actions.obligation_orchestrator import _years_to_generate
from app.clients.create_policy import normalize_vat_exempt_ceiling
from app.common.enums import EntityType, VatType
from app.clients.schemas.impact import CreationImpactItem, ClientCreationImpactResponse
from app.tax_deadline.services.obligation_plan import (
    advance_payment_deadline_plan,
    vat_deadline_plan,
)


def compute_creation_impact(
    entity_type: Optional[EntityType],
    vat_reporting_frequency: Optional[VatType],
    reference_date: Optional[date] = None,
    advance_rate=None,
) -> ClientCreationImpactResponse:
    if entity_type == EntityType.EMPLOYEE:
        raise ValueError("פתיחת לקוח מסוג שכיר אינה נתמכת במערכת")

    today = reference_date or date.today()
    years = _years_to_generate(today)
    n = len(years)
    is_exempt = vat_reporting_frequency in (VatType.EXEMPT, None)

    vat_count = sum(len(vat_deadline_plan(vat_reporting_frequency, year, today)) for year in years)
    advance_count = sum(len(advance_payment_deadline_plan(entity_type, year, today)) for year in years)
    annual_deadline_count = n
    reminder_count = vat_count + advance_count + annual_deadline_count

    items = [
        CreationImpactItem(label="קלסר פעיל", count=1),
        CreationImpactItem(label='מועדי מע"מ', count=vat_count),
        CreationImpactItem(label="מועדי מקדמות", count=advance_count),
        CreationImpactItem(label="מועד הגשת דוח שנתי", count=annual_deadline_count),
        CreationImpactItem(label="תזכורות", count=reminder_count),
        CreationImpactItem(label="תיק דוח שנתי", count=n),
    ]
    items = [i for i in items if i.count > 0]

    if is_exempt and advance_count:
        note = 'פטור ממע"מ — לא ייווצרו מועדי מע"מ תקופתיים. ייווצרו מועדי מקדמות.'
    elif is_exempt:
        note = 'פטור ממע"מ — לא ייווצרו מועדי מע"מ תקופתיים.'
    else:
        note = None

    return ClientCreationImpactResponse(
        items=items,
        years_scope=n,
        note=note,
        vat_exempt_ceiling=normalize_vat_exempt_ceiling(entity_type),
    )
