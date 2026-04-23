from datetime import date
from typing import Optional

from app.actions.action_contracts import get_binder_actions
from app.binders.models.binder import Binder, BinderStatus
from app.binders.schemas.binder import BinderResponse
from app.clients.models.legal_entity import LegalEntity


_ALLOWED_SORT_COLS = {"period_start", "days_in_office", "status", "client_name"}


class BinderListService:
    """Read helpers for binder enrichment and listing."""

    def _build_client_context_maps(self, client_record_ids: list[int]) -> tuple[dict[int, int | None], dict[int, str], dict[int, str | None]]:
        client_records = self.client_record_repo.list_by_ids(client_record_ids) if client_record_ids else []
        record_by_id = {record.id: record for record in client_records}
        legal_entity_ids = list({record.legal_entity_id for record in client_records})
        legal_entity_by_id = {
            entity.id: entity
            for entity in self.db.query(LegalEntity).filter(LegalEntity.id.in_(legal_entity_ids)).all()
        } if legal_entity_ids else {}
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

    def _matches_non_status_filters(
        self,
        binder: Binder,
        *,
        query: Optional[str],
        client_name_filter: Optional[str],
        binder_number: Optional[str],
        year: Optional[int],
        client_name: Optional[str],
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
            BinderStatus.ARCHIVED_IN_OFFICE.value: sum(
                1 for binder in binders if binder.status == BinderStatus.ARCHIVED_IN_OFFICE
            ),
        }

    def build_binder_response(
        self,
        binder: Binder,
        *,
        reference_date: Optional[date] = None,
        office_client_number: Optional[int] = None,
        client_name: Optional[str] = None,
        client_id_number: Optional[str] = None,
    ) -> BinderResponse:
        ref_date = reference_date or date.today()
        response = BinderResponse.model_validate(binder)
        response.days_in_office = (
            max(0, (ref_date - binder.period_start).days) if binder.period_start is not None else None
        )
        response.available_actions = get_binder_actions(binder)
        response.office_client_number = office_client_number
        response.client_name = client_name
        response.client_id_number = client_id_number
        return response

    def get_binder_with_client_name(self, binder_id: int) -> Optional[BinderResponse]:
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            return None
        office_client_number_map, client_name_map, client_id_number_map = self._build_client_context_maps([binder.client_record_id])
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
        client_record_id: Optional[int] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        client_name_filter: Optional[str] = None,
        binder_number: Optional[str] = None,
        year: Optional[int] = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[BinderResponse], int, dict[str, int]]:
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"
        effective_sort_by = sort_by if sort_by in _ALLOWED_SORT_COLS else "period_start"
        db_sort_by = "period_start" if effective_sort_by == "client_name" else effective_sort_by

        ref_date = reference_date or date.today()
        binders = self.binder_repo.list_active(
            client_record_id=client_record_id,
            sort_by=db_sort_by,
            sort_dir=sort_dir,
            include_returned=True,
        )

        client_record_ids = list({binder.client_record_id for binder in binders})
        office_client_number_map, client_name_map, client_id_number_map = self._build_client_context_maps(client_record_ids)

        filtered_binders: list[tuple[Binder, Optional[str]]] = []
        for binder in binders:
            current_client_name = client_name_map.get(binder.client_record_id)
            if not self._matches_non_status_filters(
                binder,
                query=query,
                client_name_filter=client_name_filter,
                binder_number=binder_number,
                year=year,
                client_name=current_client_name,
            ):
                continue
            filtered_binders.append((binder, current_client_name))

        counters = self._build_binder_counters([binder for binder, _client_name in filtered_binders])

        items: list[BinderResponse] = []
        for binder, current_client_name in filtered_binders:
            if status:
                if binder.status.value != status:
                    continue
            elif binder.status == BinderStatus.RETURNED:
                continue
            items.append(
                self.build_binder_response(
                    binder,
                    reference_date=ref_date,
                    office_client_number=office_client_number_map.get(binder.client_record_id),
                    client_name=current_client_name,
                    client_id_number=client_id_number_map.get(binder.client_record_id),
                )
            )

        if effective_sort_by == "client_name":
            items.sort(
                key=lambda r: (r.client_name or "").lower(),
                reverse=(sort_dir == "desc"),
            )

        total = len(items)
        offset = (page - 1) * page_size
        return items[offset: offset + page_size], total, counters
