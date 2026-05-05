"""Service for grouped deadline read model."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline
from app.tax_deadline.repositories.grouped_deadline_repository import GroupedDeadlineRepository
from app.tax_deadline.schemas.tax_deadline import TaxDeadlineResponse
from app.tax_deadline.schemas.grouped_deadline import GroupedDeadlineListResponse
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.tax_deadline.services.grouped_deadline_builder import build_group, build_group_key, parse_group_key
from app.tax_deadline.services.response_builder import TaxDeadlineResponseBuilder

_MAX_GROUPS = 200


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
            key = build_group_key(d.deadline_type, d.due_date)
            groups_map.setdefault(key, []).append(d)

        groups = []
        for group_key, items in list(groups_map.items())[:_MAX_GROUPS]:
            groups.append(build_group(group_key, items))

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
        parsed = parse_group_key(group_key)
        if parsed is None:
            return [], 0

        deadline_type = DeadlineType(parsed.deadline_type)
        items, total = self.repo.fetch_group_clients(
            deadline_type=deadline_type,
            due_date=parsed.due_date,
            status=status,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        client_context = self._build_client_context(items)
        responses = []
        for d in items:
            ctx = client_context.get(d.client_record_id, {})
            responses.append(
                TaxDeadlineResponseBuilder(self.db).build(
                    d,
                    client_name=ctx.get("full_name"),
                    office_client_number=ctx.get("office_client_number"),
                    user_role=user_role,
                )
            )

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
