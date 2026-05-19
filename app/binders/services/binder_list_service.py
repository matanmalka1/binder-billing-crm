from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.actions.action_registry import get_binder_actions
from app.binders.models.binder import Binder, BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.schemas.binder import BinderResponse
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository

_ALLOWED_SORT_COLS = {"period_start", "days_in_office", "status", "client_name"}
_UNSET = object()


class BinderListService:
    """Read helpers for binder enrichment and listing."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_record_repo = ClientRecordRepository(db)

    def _build_client_context_maps(
        self, client_record_ids: list[int]
    ) -> tuple[dict[int, int | None], dict[int, str], dict[int, str | None]]:
        client_records = (
            self.client_record_repo.list_by_ids(client_record_ids) if client_record_ids else []
        )
        legal_entity_ids = list({record.legal_entity_id for record in client_records})
        legal_entity_by_id = (
            {
                entity.id: entity
                for entity in self.db.scalars(
                    select(LegalEntity).where(LegalEntity.id.in_(legal_entity_ids))
                ).all()
            }
            if legal_entity_ids
            else {}
        )
        return (
            {record.id: record.office_client_number for record in client_records},
            {
                record.id: legal_entity_by_id[record.legal_entity_id].official_name
                for record in client_records
                if record.legal_entity_id in legal_entity_by_id
            },
            {
                record.id: legal_entity_by_id[record.legal_entity_id].id_number
                for record in client_records
                if record.legal_entity_id in legal_entity_by_id
            },
        )

    # TODO: remove after list_active_paginated rollout is fully settled.
    def _matches_non_status_filters(
        self,
        binder: Binder,
        *,
        query: str | None,
        client_name_filter: str | None,
        binder_number: str | None,
        year: int | None,
        client_name: str | None,
    ) -> bool:
        if query:
            query_text = query.lower()
            name_match = bool(client_name and query_text in client_name.lower())
            number_match = query_text in binder.binder_number.lower()
            if not name_match and not number_match:
                return False

        if client_name_filter and (
            not client_name or client_name_filter.lower() not in client_name.lower()
        ):
            return False

        if binder_number and binder_number.lower() not in binder.binder_number.lower():
            return False

        if year and (binder.period_start is None or binder.period_start.year != year):
            return False

        return True

    # TODO: remove after list_active_paginated rollout is fully settled.
    def _build_binder_counters(self, binders: list[Binder]) -> dict[str, int]:
        return {
            "total": len(binders),
            BinderStatus.IN_OFFICE.value: sum(
                1 for binder in binders if binder.status == BinderStatus.IN_OFFICE
            ),
            BinderStatus.CLOSED_IN_OFFICE.value: sum(
                1 for binder in binders if binder.status == BinderStatus.CLOSED_IN_OFFICE
            ),
            BinderStatus.READY_FOR_PICKUP.value: sum(
                1 for binder in binders if binder.status == BinderStatus.READY_FOR_PICKUP
            ),
            BinderStatus.RETURNED.value: sum(
                1 for binder in binders if binder.status == BinderStatus.RETURNED
            ),
        }

    def build_binder_response(
        self,
        binder: Binder,
        *,
        reference_date: date | None = None,
        office_client_number: int | None | object = _UNSET,
        client_name: str | None | object = _UNSET,
        client_id_number: str | None | object = _UNSET,
    ) -> BinderResponse:
        if office_client_number is _UNSET or client_name is _UNSET or client_id_number is _UNSET:
            office_client_number_map, client_name_map, client_id_number_map = (
                self._build_client_context_maps([binder.client_record_id])
            )
            if office_client_number is _UNSET:
                office_client_number = office_client_number_map.get(binder.client_record_id)
            if client_name is _UNSET:
                client_name = client_name_map.get(binder.client_record_id)
            if client_id_number is _UNSET:
                client_id_number = client_id_number_map.get(binder.client_record_id)

        ref_date = reference_date or date.today()
        response = BinderResponse.model_validate(binder)
        response.days_in_office = (
            max(0, (ref_date - binder.period_start).days)
            if binder.period_start is not None
            else None
        )
        response.available_actions = get_binder_actions(binder)
        response.office_client_number = office_client_number
        response.client_name = client_name
        response.client_id_number = client_id_number
        return response

    def get_binder_with_client_name(self, binder_id: int) -> BinderResponse | None:
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            return None
        office_client_number_map, client_name_map, client_id_number_map = (
            self._build_client_context_maps([binder.client_record_id])
        )
        return self.build_binder_response(
            binder,
            reference_date=date.today(),
            office_client_number=office_client_number_map.get(binder.client_record_id),
            client_name=client_name_map.get(binder.client_record_id),
            client_id_number=client_id_number_map.get(binder.client_record_id),
        )

    def list_binders_enriched(
        self,
        *,
        client_record_id: int | None = None,
        status: str | None = None,
        query: str | None = None,
        client_name_filter: str | None = None,
        binder_number: str | None = None,
        year: int | None = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
        reference_date: date | None = None,
    ) -> tuple[list[BinderResponse], int, dict[str, int]]:
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"
        effective_sort_by = sort_by if sort_by in _ALLOWED_SORT_COLS else "period_start"

        ref_date = reference_date or date.today()
        binders, total = self.binder_repo.list_active_paginated(
            client_record_id=client_record_id,
            status=status,
            include_returned=(status is not None),
            query=query,
            client_name_filter=client_name_filter,
            binder_number=binder_number,
            year=year,
            sort_by=effective_sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size,
        )
        counters = self.binder_repo.count_by_status_filtered(
            client_record_id=client_record_id,
            query=query,
            client_name_filter=client_name_filter,
            binder_number=binder_number,
            year=year,
        )

        client_record_ids = list({binder.client_record_id for binder in binders})
        office_client_number_map, client_name_map, client_id_number_map = (
            self._build_client_context_maps(client_record_ids)
        )

        items: list[BinderResponse] = []
        for binder in binders:
            items.append(
                self.build_binder_response(
                    binder,
                    reference_date=ref_date,
                    office_client_number=office_client_number_map.get(binder.client_record_id),
                    client_name=client_name_map.get(binder.client_record_id),
                    client_id_number=client_id_number_map.get(binder.client_record_id),
                )
            )

        return items, total, counters
