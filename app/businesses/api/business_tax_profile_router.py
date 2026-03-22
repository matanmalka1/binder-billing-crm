from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.schemas.business_tax_profile_schemas import (
    BusinessTaxProfileResponse,
    BusinessTaxProfileUpdateRequest,
)
from app.businesses.services.business_tax_profile_service import BusinessTaxProfileService

router = APIRouter(
    prefix="/businesses",
    tags=["business-tax-profile"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{business_id}/tax-profile", response_model=BusinessTaxProfileResponse)
def get_tax_profile(business_id: int, db: DBSession, user: CurrentUser):
    """Get tax profile for a specific business."""
    service = BusinessTaxProfileService(db)
    return service.get_profile_or_empty(business_id)


@router.patch(
    "/{business_id}/tax-profile",
    response_model=BusinessTaxProfileResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def update_tax_profile(
    business_id: int,
    request: BusinessTaxProfileUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update (or create) tax profile for a specific business (ADVISOR only)."""
    service = BusinessTaxProfileService(db)
    update_data = request.model_dump(exclude_unset=True)
    profile = service.update_profile(business_id, **update_data)
    return BusinessTaxProfileResponse.model_validate(profile)
