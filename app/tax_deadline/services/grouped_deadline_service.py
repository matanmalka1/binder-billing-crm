"""Service for grouped deadline read model.

Groups flat TaxDeadline rows by (deadline_type × period/tax_year × due_date)
and computes per-group aggregates. No DB schema changes needed.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus, UrgencyLevel
from app.tax_deadline.repositories.grouped_deadline_repository import GroupedDeadlineRepository
from app.tax_deadline.services.urgency import compute_deadline_urgency
from app.tax_deadline.schemas.tax_deadline import TaxDeadlineResponse
from app.tax_deadline.schemas.grouped_deadline import (
    DeadlineGroup,
    DeadlineGroupKey,
    GroupedDeadlineListResponse,
)
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository

_MAX_GROUPS = 200
_URGENCY_ORDER = {
    UrgencyLevel.OVERDUE: 0,
    UrgencyLevel.CRITICAL: 1,
    UrgencyLevel.WARNING: 2,
    UrgencyLevel.NORMAL: 3,
    UrgencyLevel.NONE: 4,
}


def _build_group_key_str(
    deadline_type,
    period: Optional[str],
    tax_year: Optional[int],
    due_date: date,
) -> str:
    type_str = deadline_type.value if hasattr(deadline_type, "value") else str(deadline_type)
    period_part = period or (str(tax_year) if tax_year else "none")
    return f"{type_str}__{period_part}__{due_date.isoformat()}"


def _parse_group_key(group_key: str) -> DeadlineGroupKey:
    parts = group_key.split("__")
    if len(parts) != 3:
        return None
    deadline_type_raw, period_part, due_date_str = parts
    period = period_part if "-" in period_part and len(period_part) == 7 else None
    tax_year_val = int(period_part) if period_part.isdigit() else None
    return DeadlineGroupKey(
        deadline_type=deadline_type_raw,
        period=period,
        tax_year=tax_year_val,
        due_date=date.fromisoformat(due_date_str),
    )


def _worst_urgency(urgencies: list[UrgencyLevel]) -> UrgencyLevel:
    if not urgencies:
        return UrgencyLevel.NONE
    return min(urgencies, key=lambda u: _URGENCY_ORDER[u])


class GroupedDeadlineService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = GroupedDeadlineRepository(db)
        self.client_record_repo = ClientRecordRepository(db)

    def list_groups(
        self,
        *,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        client_name: Optional[str] = None,
    ) -> GroupedDeadlineListResponse:
        client_name_ids = self._resolve_client_name_ids(client_name)
        if client_name is not None and not client_name_ids:
            return GroupedDeadlineListResponse(groups=[], total_groups=0, total_client_deadlines=0)

        deadlines = self.repo.fetch_for_grouping(
            status=status,
            deadline_type=deadline_type,
            due_from=due_from,
            due_to=due_to,
            client_name_ids=client_name_ids,
        )

        groups_map: dict[str, list[TaxDeadline]] = {}
        for d in deadlines:
            key = _build_group_key_str(d.deadline_type, d.period, d.tax_year, d.due_date)
            groups_map.setdefault(key, []).append(d)

        groups = []
        for group_key, items in list(groups_map.items())[:_MAX_GROUPS]:
            groups.append(_build_group(group_key, items))

        return GroupedDeadlineListResponse(
            groups=groups,
            total_groups=len(groups),
            total_client_deadlines=len(deadlines),
        )

    def get_group_clients(
        self,
        group_key: str,
        *,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        user_role=None,
    ) -> tuple[list[TaxDeadlineResponse], int]:
        from app.actions.report_deadline_actions import get_tax_deadline_actions

        parsed = _parse_group_key(group_key)
        if parsed is None:
            return [], 0

        deadline_type = DeadlineType(parsed.deadline_type)
        items, total = self.repo.fetch_group_clients(
            deadline_type=deadline_type,
            due_date=parsed.due_date,
            period=parsed.period,
            tax_year=parsed.tax_year,
            status=status,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        client_context = self._build_client_context(items)
        responses = []
        for d in items:
            ctx = client_context.get(d.client_record_id, {})
            r = TaxDeadlineResponse.model_validate(d)
            r.client_name = ctx.get("full_name")
            r.office_client_number = ctx.get("office_client_number")
            r.urgency_level = compute_deadline_urgency(d)
            r.available_actions = get_tax_deadline_actions(d, user_role=user_role)
            responses.append(r)

        return responses, total

    def _resolve_client_name_ids(self, client_name: Optional[str]) -> Optional[list[int]]:
        if not client_name:
            return None
        from app.businesses.repositories.business_repository import BusinessRepository
        businesses = BusinessRepository(self.db).list(search=client_name, page=1, page_size=500)
        ids = list({b.client_record_id for b in businesses})
        return ids if ids else []

    def _build_client_context(self, deadlines: list[TaxDeadline]) -> dict:
        ids = list({d.client_record_id for d in deadlines})
        records = self.client_record_repo.list_by_ids(ids) if ids else []
        legal_repo = LegalEntityRepository(self.db)
        return {
            r.id: {
                "full_name": (le := legal_repo.get_by_id(r.legal_entity_id)) and le.official_name,
                "office_client_number": r.office_client_number,
            }
            for r in records
        }


def _build_group(group_key: str, items: list[TaxDeadline]) -> DeadlineGroup:
    today = date.today()
    urgencies = [compute_deadline_urgency(d, today) for d in items]
    pending = [d for d in items if d.status == TaxDeadlineStatus.PENDING]
    completed = [d for d in items if d.status == TaxDeadlineStatus.COMPLETED]
    amounts = [Decimal(str(d.payment_amount)) for d in items if d.payment_amount is not None]
    open_amounts = [
        Decimal(str(d.payment_amount))
        for d in pending
        if d.payment_amount is not None
    ]

    representative = items[0]
    return DeadlineGroup(
        group_key=group_key,
        deadline_type=representative.deadline_type,
        period=representative.period,
        tax_year=representative.tax_year,
        due_date=representative.due_date,
        total_clients=len(items),
        pending_count=len(pending),
        completed_count=len(completed),
        canceled_count=len(items) - len(pending) - len(completed),
        overdue_count=sum(1 for u in urgencies if u == UrgencyLevel.OVERDUE),
        total_amount=sum(amounts) if amounts else None,
        open_amount=sum(open_amounts) if open_amounts else None,
        worst_urgency=_worst_urgency(urgencies),
    )
