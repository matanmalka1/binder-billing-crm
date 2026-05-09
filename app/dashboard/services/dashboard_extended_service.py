from datetime import date
from types import SimpleNamespace
from typing import Optional

from sqlalchemy.orm import Session

from app.charge.models.charge import ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.users.models.user import UserRole
from app.dashboard.services.dashboard_extended_builders import unpaid_charge_attention_item

_UNPAID_CHARGES_FETCH_LIMIT = 500


class DashboardExtendedService:
    """Extended dashboard: alerts, and attention items."""

    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.legal_entity_repo = LegalEntityRepository(db)
        self.charge_repo = ChargeRepository(db)

    def get_attention_items(
        self,
        user_role: Optional[UserRole] = None,
        reference_date: Optional[date] = None,
    ) -> list[dict]:
        if reference_date is None:
            reference_date = date.today()

        items = []
        if user_role == UserRole.ADVISOR:
            unpaid_charges = self.charge_repo.list_charges(
                status=ChargeStatus.ISSUED.value,
                page=1,
                page_size=_UNPAID_CHARGES_FETCH_LIMIT,
            )
            if unpaid_charges:
                charge_business_ids = list(
                    {c.business_id for c in unpaid_charges if c.business_id is not None}
                )
                charge_businesses = self.business_repo.list_by_ids(charge_business_ids)
                charge_business_map = {b.id: b for b in charge_businesses}
                charge_client_record_ids = list(
                    {
                        c.client_record_id
                        for c in unpaid_charges
                        if c.client_record_id is not None
                    }
                )
                charge_client_records = self.client_record_repo.list_by_ids(
                    charge_client_record_ids
                )
                legal_entity_ids = list(
                    {r.legal_entity_id for r in charge_client_records}
                )
                legal_entities = [
                    self.legal_entity_repo.get_by_id(eid) for eid in legal_entity_ids
                ]
                legal_entity_map = {e.id: e.official_name for e in legal_entities if e}
                client_record_map = {r.id: r for r in charge_client_records}
                for charge in unpaid_charges:
                    business = charge_business_map.get(charge.business_id)
                    if charge.business_id is not None and not business:
                        continue
                    client_record = client_record_map.get(charge.client_record_id)
                    client_display_name = (
                        legal_entity_map.get(client_record.legal_entity_id, "")
                        if client_record
                        else ""
                    )
                    if business is None:
                        business = SimpleNamespace(
                            id=None,
                            business_name=client_display_name,
                            full_name=client_display_name,
                        )
                    items.append(
                        unpaid_charge_attention_item(
                            charge,
                            business,
                            client_display_name,
                            reference_date,
                        )
                    )

        return items
