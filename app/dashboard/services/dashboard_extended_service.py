from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.models.charge import ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.binders.services.signals_service import SignalsService
from app.users.models.user import UserRole
from app.dashboard.services.dashboard_extended_builders import (
    idle_attention_item,
    ready_attention_item,
    unpaid_charge_attention_item,
    work_queue_item,
)

# Hard limits for in-memory aggregations.
# Proper fix: persist derived state or push aggregation to SQL (Sprint 10+).
_ACTIVE_BINDERS_FETCH_LIMIT = 1000
_UNPAID_CHARGES_FETCH_LIMIT = 500


class DashboardExtendedService:
    """Extended dashboard: work queue, alerts, and attention items."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.business_repo = BusinessRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.signals_service = SignalsService(db)
        self._cached_active_binders_with_businesses: Optional[list[tuple]] = None

    def _active_binders_with_businesses(self) -> list[tuple]:
        """Fetch active binders once and attach client objects to avoid N+1.

        Bounded to _ACTIVE_BINDERS_FETCH_LIMIT. Binders beyond the ceiling
        are excluded from dashboard calculations (known debt).
        """
        if self._cached_active_binders_with_businesses is None:
            binders = self.binder_repo.list_active(
                page=1, page_size=_ACTIVE_BINDERS_FETCH_LIMIT
            )
            client_ids = list({binder.client_id for binder in binders})
            businesses = self.business_repo.list_by_client_ids(client_ids)
            business_map = {}
            for business in businesses:
                business_map.setdefault(business.client_id, business)
            self._cached_active_binders_with_businesses = [
                (binder, business_map.get(binder.client_id))
                for binder in binders
                if business_map.get(binder.client_id)
            ]
        return self._cached_active_binders_with_businesses

    def get_work_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[dict], int]:
        if reference_date is None:
            reference_date = date.today()

        items = []
        for binder, business in self._active_binders_with_businesses():
            signals = self.signals_service.compute_binder_signals(binder, reference_date)
            items.append(work_queue_item(binder, business, signals, reference_date))
        total = len(items)
        offset = (page - 1) * page_size
        return items[offset : offset + page_size], total

    def get_attention_items(
        self,
        user_role: Optional[UserRole] = None,
        reference_date: Optional[date] = None,
    ) -> list[dict]:
        if reference_date is None:
            reference_date = date.today()

        items = []
        for binder, business in self._active_binders_with_businesses():
            if self.signals_service.is_idle_binder(binder, reference_date):
                items.append(idle_attention_item(binder, business, reference_date))
            if binder.status == BinderStatus.READY_FOR_PICKUP:
                items.append(ready_attention_item(binder, business))

        if user_role == UserRole.ADVISOR:
            unpaid_charges = self.charge_repo.list_charges(
                status=ChargeStatus.ISSUED.value,
                page=1,
                page_size=_UNPAID_CHARGES_FETCH_LIMIT,
            )
            if unpaid_charges:
                charge_business_ids = list({c.business_id for c in unpaid_charges})
                charge_businesses = self.business_repo.list_by_ids(charge_business_ids)
                charge_business_map = {c.id: c for c in charge_businesses}
                for charge in unpaid_charges:
                    business = charge_business_map.get(charge.business_id)
                    if not business:
                        continue
                    items.append(unpaid_charge_attention_item(charge, business))

        return items
