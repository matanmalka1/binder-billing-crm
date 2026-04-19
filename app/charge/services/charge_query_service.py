from typing import Optional, Union

from sqlalchemy.orm import Session

from app.charge.models.charge import Charge
from app.charge.repositories.charge_repository import ChargeRepository
from app.charge.schemas.charge import ChargeListResponse, ChargeListStats, ChargeStatusStat, ChargeResponse, ChargeResponseSecretary
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.users.models.user import UserRole


class ChargeQueryService:
    """Read-only charge listing and enrichment logic."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)

    def enrich_charge_context(self, charge: Charge) -> tuple[str | None, int | None]:
        """Return display name and office client number for a single charge."""
        if charge.business_id is not None:
            businesses = self.business_repo.list_by_ids([charge.business_id])
            if businesses:
                client = self.client_repo.get_by_id(charge.client_id)
                return businesses[0].full_name, client.office_client_number if client else None
        client = self.client_repo.get_by_id(charge.client_id)
        if client:
            return client.full_name, client.office_client_number
        return None, None

    def list_charges(
        self,
        business_id: Optional[int] = None,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Charge], int, dict[int, str], dict[int, int | None]]:
        """
        List charges with pagination.

        Returns (items, total, business_name_map, office_client_number_map).
        """
        client_record = ClientRecordRepository(self.db).get_by_client_id(client_id) if client_id is not None else None
        if client_record is not None:
            items = self.charge_repo.list_charges_by_client_record(
                client_record_id=client_record.id,
                business_id=business_id,
                status=status,
                charge_type=charge_type,
                page=page,
                page_size=page_size,
            )
            total = self.charge_repo.count_charges_by_client_record(
                client_record_id=client_record.id,
                business_id=business_id,
                status=status,
                charge_type=charge_type,
            )
        else:
            items = self.charge_repo.list_charges(
                client_id=client_id,
                business_id=business_id,
                status=status,
                charge_type=charge_type,
                page=page,
                page_size=page_size,
            )
            total = self.charge_repo.count_charges(
                client_id=client_id,
                business_id=business_id,
                status=status,
                charge_type=charge_type,
            )

        business_ids = list({c.business_id for c in items if c.business_id is not None})
        businesses = self.business_repo.list_by_ids(business_ids) if business_ids else []
        business_name_by_id: dict[int, str] = {c.id: c.full_name for c in businesses}
        client_ids = list({c.client_id for c in items})
        clients = self.client_repo.list_by_ids(client_ids) if client_ids else []
        client_name_by_id = {c.id: c.full_name for c in clients}
        office_client_number_by_id = {c.id: c.office_client_number for c in clients}
        business_name_map: dict[int, str] = {
            c.id: business_name_by_id.get(c.business_id) or client_name_by_id.get(c.client_id)
            for c in items
        }
        office_client_number_map: dict[int, int | None] = {
            c.id: office_client_number_by_id.get(c.client_id)
            for c in items
        }

        return items, total, business_name_map, office_client_number_map

    def list_charges_for_role(
        self,
        user_role: UserRole,
        business_id: Optional[int] = None,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ChargeListResponse:
        """List charges serialized and role-shaped in one call."""
        items, total, business_name_map, office_client_number_map = self.list_charges(
            business_id=business_id,
            client_id=client_id,
            status=status,
            charge_type=charge_type,
            page=page,
            page_size=page_size,
        )
        schema = ChargeResponseSecretary if user_role == UserRole.SECRETARY else ChargeResponse

        def _enrich(charge: Charge) -> Union[ChargeResponse, ChargeResponseSecretary]:
            data = schema.model_validate(charge).model_dump()
            data["business_name"] = business_name_map.get(charge.id)
            data["office_client_number"] = office_client_number_map.get(charge.id)
            return schema(**data)

        client_record = ClientRecordRepository(self.db).get_by_client_id(client_id) if client_id is not None else None
        raw = self.charge_repo.stats_by_status(
            client_id=client_id,
            client_record_id=client_record.id if client_record else None,
            charge_type=charge_type,
        )
        def _stat(key: str) -> ChargeStatusStat:
            d = raw.get(key, {})
            return ChargeStatusStat(count=d.get("count", 0), amount=d.get("amount", "0"))
        stats = ChargeListStats(
            draft=_stat("draft"),
            issued=_stat("issued"),
            paid=_stat("paid"),
            canceled=_stat("canceled"),
        )
        return ChargeListResponse(
            items=[_enrich(c) for c in items],
            page=page,
            page_size=page_size,
            total=total,
            stats=stats,
        )
