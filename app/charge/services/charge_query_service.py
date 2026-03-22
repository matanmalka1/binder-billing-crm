from typing import Optional, Union

from sqlalchemy.orm import Session

from app.charge.models.charge import Charge
from app.charge.repositories.charge_repository import ChargeRepository
from app.charge.schemas.charge import ChargeListResponse, ChargeResponse, ChargeResponseSecretary
from app.businesses.repositories.business_repository import BusinessRepository
from app.users.models.user import UserRole


class ChargeQueryService:
    """Read-only charge listing and enrichment logic."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.business_repo = BusinessRepository(db)

    def enrich_business_name(self, charge: Charge) -> str | None:
        """Return the business full_name for a single charge."""
        businesses = self.business_repo.list_by_ids([charge.business_id])
        return businesses[0].full_name if businesses else None

    def list_charges(
        self,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Charge], int, dict[int, str]]:
        """
        List charges with pagination.

        Returns (items, total, business_name_map) where business_name_map maps
        business_id → full_name for all charges in the page.
        """
        items = self.charge_repo.list_charges(
            business_id=business_id,
            status=status,
            charge_type=charge_type,
            page=page,
            page_size=page_size,
        )
        total = self.charge_repo.count_charges(
            business_id=business_id, status=status, charge_type=charge_type
        )

        business_ids = list({c.business_id for c in items})
        businesses = self.business_repo.list_by_ids(business_ids)
        business_name_map: dict[int, str] = {c.id: c.full_name for c in businesses}

        return items, total, business_name_map

    def list_charges_for_role(
        self,
        user_role: UserRole,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ChargeListResponse:
        """List charges serialized and role-shaped in one call."""
        items, total, business_name_map = self.list_charges(
            business_id=business_id,
            status=status,
            charge_type=charge_type,
            page=page,
            page_size=page_size,
        )
        schema = ChargeResponseSecretary if user_role == UserRole.SECRETARY else ChargeResponse

        def _enrich(charge: Charge) -> Union[ChargeResponse, ChargeResponseSecretary]:
            data = schema.model_validate(charge).model_dump()
            data["business_name"] = business_name_map.get(charge.business_id)
            return schema(**data)

        return ChargeListResponse(
            items=[_enrich(c) for c in items],
            page=page,
            page_size=page_size,
            total=total,
        )
