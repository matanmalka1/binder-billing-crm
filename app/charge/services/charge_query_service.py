from typing import Optional

from sqlalchemy.orm import Session

from app.actions.charge_actions import get_charge_actions
from app.charge.models.charge import Charge
from app.charge.repositories.charge_repository import ChargeRepository
from app.charge.schemas.charge import ChargeListResponse, ChargeListStats, ChargeStatusStat, ChargeResponse, ChargeResponseSecretary
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.users.models.user import UserRole


class ChargeQueryService:
    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.business_repo = BusinessRepository(db)

    def enrich_charge_context(self, charge: Charge) -> tuple[str | None, int | None]:
        client_record = ClientRecordRepository(self.db).get_by_id(charge.client_record_id)
        legal_entity = (
            self.db.query(LegalEntity).filter(LegalEntity.id == client_record.legal_entity_id).first()
            if client_record
            else None
        )
        if charge.business_id is not None:
            businesses = self.business_repo.list_by_ids([charge.business_id])
            if businesses:
                return businesses[0].full_name, client_record.office_client_number if client_record else None
        if client_record and legal_entity:
            return legal_entity.official_name, client_record.office_client_number
        return None, None

    def list_charges(
        self,
        business_id: Optional[int] = None,
        client_record_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Charge], int, dict[int, str], dict[int, int | None]]:
        client_record = ClientRecordRepository(self.db).get_by_id(client_record_id) if client_record_id is not None else None
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
                client_record_id=client_record_id,
                business_id=business_id,
                status=status,
                charge_type=charge_type,
                page=page,
                page_size=page_size,
            )
            total = self.charge_repo.count_charges(
                client_record_id=client_record_id,
                business_id=business_id,
                status=status,
                charge_type=charge_type,
            )

        business_ids = list({c.business_id for c in items if c.business_id is not None})
        businesses = self.business_repo.list_by_ids(business_ids) if business_ids else []
        business_name_by_id = {c.id: c.full_name for c in businesses}
        client_record_ids = list({c.client_record_id for c in items})
        client_records = ClientRecordRepository(self.db).list_by_ids(client_record_ids) if client_record_ids else []
        record_by_id = {record.id: record for record in client_records}
        legal_entity_ids = list({record.legal_entity_id for record in client_records})
        legal_entity_by_id = {
            entity.id: entity
            for entity in self.db.query(LegalEntity).filter(LegalEntity.id.in_(legal_entity_ids)).all()
        } if legal_entity_ids else {}
        business_name_map = {
            c.id: business_name_by_id.get(c.business_id)
            or (
                legal_entity_by_id[record_by_id[c.client_record_id].legal_entity_id].official_name
                if c.client_record_id in record_by_id
                and record_by_id[c.client_record_id].legal_entity_id in legal_entity_by_id
                else None
            )
            for c in items
        }
        office_client_number_map = {
            c.id: record_by_id[c.client_record_id].office_client_number if c.client_record_id in record_by_id else None
            for c in items
        }

        return items, total, business_name_map, office_client_number_map

    def list_charges_for_role(
        self,
        user_role: UserRole,
        business_id: Optional[int] = None,
        client_record_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ChargeListResponse:
        items, total, business_name_map, office_client_number_map = self.list_charges(
            business_id=business_id,
            client_record_id=client_record_id,
            status=status,
            charge_type=charge_type,
            page=page,
            page_size=page_size,
        )
        schema = ChargeResponseSecretary if user_role == UserRole.SECRETARY else ChargeResponse

        def _enrich(charge: Charge) -> ChargeResponse | ChargeResponseSecretary:
            data = schema.model_validate(charge).model_dump()
            data["business_name"] = business_name_map.get(charge.id)
            data["office_client_number"] = office_client_number_map.get(charge.id)
            data["available_actions"] = get_charge_actions(charge, user_role=user_role)
            return schema(**data)

        client_record = ClientRecordRepository(self.db).get_by_id(client_record_id) if client_record_id is not None else None
        raw = self.charge_repo.stats_by_status(
            client_record_id=client_record.id if client_record else None,
            charge_type=charge_type,
        )
        def _stat(key: str) -> ChargeStatusStat:
            d = raw.get(key, {})
            return ChargeStatusStat(count=d.get("count", 0), amount=d.get("amount", "0"))
        stats = ChargeListStats(draft=_stat("draft"), issued=_stat("issued"), paid=_stat("paid"), canceled=_stat("canceled"))
        return ChargeListResponse(
            items=[_enrich(c) for c in items],
            page=page,
            page_size=page_size,
            total=total,
            stats=stats,
        )
