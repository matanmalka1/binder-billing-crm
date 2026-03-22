from datetime import date
from typing import Optional

from app.actions.action_contracts import get_binder_actions
from app.binders.models.binder import Binder
from app.binders.schemas.binder import BinderResponse
from app.binders.services.signals_service import SignalsService
from app.binders.services.work_state_service import WorkStateService


_ALLOWED_SORT_COLS = {"period_start", "days_in_office", "status", "client_name"}


class BinderListService:
    """Read helpers for binder enrichment and listing."""

    def build_binder_response(
        self,
        binder: Binder,
        *,
        reference_date: Optional[date] = None,
        work_state: Optional[str] = None,
        signals: Optional[list[str]] = None,
        client_name: Optional[str] = None,
        signals_service: Optional[SignalsService] = None,
    ) -> BinderResponse:
        ref_date = reference_date or date.today()
        service = signals_service or SignalsService(self.db)
        response = BinderResponse.model_validate(binder)
        response.days_in_office = (ref_date - binder.period_start).days
        response.work_state = work_state or WorkStateService.derive_work_state(
            binder, ref_date, self.db,
        ).value
        response.signals = signals if signals is not None else service.compute_binder_signals(
            binder, ref_date,
        )
        response.available_actions = get_binder_actions(binder)
        response.client_name = client_name
        return response

    def get_binder_with_client_name(self, binder_id: int) -> Optional[BinderResponse]:
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            return None
        client = self.client_repo.get_by_id(binder.client_id)
        return self.build_binder_response(
            binder,
            reference_date=date.today(),
            client_name=client.full_name if client else None,
        )

    def list_binders_enriched(
        self,
        *,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        work_state: Optional[str] = None,
        query: Optional[str] = None,
        client_name_filter: Optional[str] = None,
        binder_number: Optional[str] = None,
        year: Optional[int] = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[BinderResponse], int]:
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"
        effective_sort_by = sort_by if sort_by in _ALLOWED_SORT_COLS else "period_start"
        db_sort_by = "period_start" if effective_sort_by == "client_name" else effective_sort_by

        ref_date = reference_date or date.today()
        signals_service = SignalsService(self.db)
        binders = self.binder_repo.list_active(
            client_id=client_id,
            status=status,
            sort_by=db_sort_by,
            sort_dir=sort_dir,
        )

        client_ids = list({binder.client_id for binder in binders})
        clients = self.client_repo.list_by_ids(client_ids) if client_ids else []
        client_name_map = {c.id: c.full_name for c in clients}

        items: list[BinderResponse] = []
        for binder in binders:
            current_work_state = WorkStateService.derive_work_state(
                binder, ref_date, self.db,
            ).value
            current_signals = signals_service.compute_binder_signals(binder, ref_date)

            if work_state and current_work_state != work_state:
                continue

            current_client_name = client_name_map.get(binder.client_id)

            if query:
                query_text = query.lower()
                name_match = bool(current_client_name and query_text in current_client_name.lower())
                number_match = query_text in binder.binder_number.lower()
                if not name_match and not number_match:
                    continue

            if client_name_filter and (
                not current_client_name
                or client_name_filter.lower() not in current_client_name.lower()
            ):
                continue

            if binder_number and binder_number.lower() not in binder.binder_number.lower():
                continue

            if year and binder.period_start.year != year:
                continue

            items.append(
                self.build_binder_response(
                    binder,
                    reference_date=ref_date,
                    work_state=current_work_state,
                    signals=current_signals,
                    client_name=current_client_name,
                    signals_service=signals_service,
                )
            )

        if effective_sort_by == "client_name":
            items.sort(
                key=lambda r: (r.client_name or "").lower(),
                reverse=(sort_dir == "desc"),
            )

        total = len(items)
        offset = (page - 1) * page_size
        return items[offset: offset + page_size], total