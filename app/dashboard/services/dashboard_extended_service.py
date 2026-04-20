from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.models.charge import ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.users.models.user import UserRole
from app.dashboard.services.dashboard_extended_builders import (
    ready_attention_item,
    unpaid_charge_attention_item,
)

# Hard limits for in-memory aggregations.
# Proper fix: persist derived state or push aggregation to SQL (Sprint 10+).
_ACTIVE_BINDERS_FETCH_LIMIT = 1000
_UNPAID_CHARGES_FETCH_LIMIT = 500


class DashboardExtendedService:
    """Extended dashboard: alerts, and attention items."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.charge_repo = ChargeRepository(db)
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
            client_record_ids = list({binder.client_record_id for binder in binders})
            record_by_id = {
                record.id: record
                for record in (
                    self.client_record_repo.get_by_id(client_record_id)
                    for client_record_id in client_record_ids
                )
                if record is not None
            }
            legal_entity_ids = [record.legal_entity_id for record in record_by_id.values()]
            businesses = self.business_repo.list_by_legal_entity_ids(legal_entity_ids)
            business_map = {}
            for business in businesses:
                key = next(
                    (
                        client_record_id
                        for client_record_id, record in record_by_id.items()
                        if record.legal_entity_id == business.legal_entity_id
                    ),
                    None,
                )
                if key is None:
                    continue
                business_map.setdefault(key, business)
            self._cached_active_binders_with_businesses = [
                (binder, business_map.get(binder.client_record_id))
                for binder in binders
                if business_map.get(binder.client_record_id)
            ]
        return self._cached_active_binders_with_businesses

    def get_attention_items(
        self,
        user_role: Optional[UserRole] = None,
        reference_date: Optional[date] = None,
    ) -> list[dict]:
        if reference_date is None:
            reference_date = date.today()

        items = []
        for binder, business in self._active_binders_with_businesses():
            if binder.status == BinderStatus.READY_FOR_PICKUP:
                items.append(ready_attention_item(binder, business))

        if user_role == UserRole.ADVISOR:
            unpaid_charges = self.charge_repo.list_charges(
                status=ChargeStatus.ISSUED.value,
                page=1,
                page_size=_UNPAID_CHARGES_FETCH_LIMIT,
            )
            if unpaid_charges:
                charge_business_ids = list({c.business_id for c in unpaid_charges if c.business_id is not None})
                charge_businesses = self.business_repo.list_by_ids(charge_business_ids)
                charge_business_map = {c.id: c for c in charge_businesses}
                for charge in unpaid_charges:
                    business = charge_business_map.get(charge.business_id)
                    if not business:
                        continue
                    items.append(unpaid_charge_attention_item(charge, business))

        return items
