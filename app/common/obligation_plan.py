from dataclasses import dataclass
from typing import Optional

from app.common.enums import AdvancePaymentFrequency, EntityType, VatType


@dataclass(frozen=True, slots=True)
class PeriodicObligationPlan:
    period: str
    period_months_count: int


def vat_obligation_plan(
    vat_type: Optional[VatType],
    year: int,
) -> list[PeriodicObligationPlan]:
    if vat_type in (VatType.EXEMPT, None):
        return []

    plans: list[PeriodicObligationPlan] = []
    if vat_type == VatType.MONTHLY:
        for month in range(1, 13):
            period = f"{year}-{month:02d}"
            plans.append(
                PeriodicObligationPlan(
                    period=period,
                    period_months_count=1,
                )
            )
    elif vat_type == VatType.BIMONTHLY:
        for period_start in range(1, 12, 2):
            period = f"{year}-{period_start:02d}"
            plans.append(
                PeriodicObligationPlan(
                    period=period,
                    period_months_count=2,
                )
            )
    return plans


def advance_payment_obligation_plan(
    *,
    frequency: AdvancePaymentFrequency,
    year: int,
    entity_type: EntityType | None = None,
) -> list[PeriodicObligationPlan]:
    if entity_type == EntityType.EMPLOYEE:
        return []

    if frequency == AdvancePaymentFrequency.BIMONTHLY:
        period_starts = [1, 3, 5, 7, 9, 11]
        period_months_count = 2
    else:
        period_starts = list(range(1, 13))
        period_months_count = 1

    plans = []
    for month in period_starts:
        period = f"{year}-{month:02d}"
        plans.append(
            PeriodicObligationPlan(
                period=period,
                period_months_count=period_months_count,
            )
        )
    return plans
