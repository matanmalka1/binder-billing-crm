from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.annual_reports.services.deadlines import standard_deadline
from app.clients.constants import ENTITY_TYPE_TO_REPORT_CLIENT_TYPE
from app.common.enums import EntityType, VatType
from app.tax_deadline.services.due_date_rules import periodic_due_date


@dataclass(frozen=True, slots=True)
class PeriodicDeadlinePlan:
    due_date: date
    period: str


def vat_deadline_plan(
    vat_type: Optional[VatType],
    year: int,
    reference_date: date,
) -> list[PeriodicDeadlinePlan]:
    if vat_type in (VatType.EXEMPT, None):
        return []

    due_dates: list[PeriodicDeadlinePlan] = []
    if vat_type == VatType.MONTHLY:
        for month in range(1, 13):
            filing_month = month + 1 if month < 12 else 1
            filing_year = year if month < 12 else year + 1
            period = f"{year}-{month:02d}"
            due_dates.append(
                PeriodicDeadlinePlan(
                    due_date=periodic_due_date(filing_year, filing_month, period),
                    period=period,
                )
            )
    elif vat_type == VatType.BIMONTHLY:
        for period_start in range(1, 12, 2):
            period_end = period_start + 1
            filing_month = period_start + 2 if period_start + 2 <= 12 else 1
            filing_year = year if filing_month != 1 else year + 1
            period = f"{year}-{period_start:02d}"
            calendar_period = f"{year}-{period_end:02d}"
            due_dates.append(
                PeriodicDeadlinePlan(
                    due_date=periodic_due_date(filing_year, filing_month, calendar_period),
                    period=period,
                )
            )
    return [item for item in due_dates if item.due_date >= reference_date]


def advance_payment_deadline_plan(
    entity_type: Optional[EntityType],
    year: int,
    reference_date: date,
) -> list[PeriodicDeadlinePlan]:
    if entity_type == EntityType.EMPLOYEE:
        return []

    due_dates = []
    for month in range(1, 13):
        period = f"{year}-{month:02d}"
        due_dates.append(
            PeriodicDeadlinePlan(
                due_date=periodic_due_date(year, month, period),
                period=period,
            )
        )
    return [item for item in due_dates if item.due_date >= reference_date]


def annual_report_due_date(entity_type: Optional[EntityType], year: int) -> date:
    client_type = ENTITY_TYPE_TO_REPORT_CLIENT_TYPE.get(entity_type)
    return standard_deadline(year, client_type=client_type).date()
