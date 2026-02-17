from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.models.client_tax_profile import VatType
from app.schemas.client_tax_profile import TaxProfileResponse, TaxProfileUpdateRequest
from app.services.client_tax_profile_service import ClientTaxProfileService

router = APIRouter(
    prefix="/clients",
    tags=["client-tax-profile"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/tax-profile", response_model=TaxProfileResponse)
def get_tax_profile(client_id: int, db: DBSession, user: CurrentUser):
    service = ClientTaxProfileService(db)
    from app.repositories.client_repository import ClientRepository
    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    profile = service.get_profile(client_id)
    if profile is None:
        return TaxProfileResponse(client_id=client_id)
    return TaxProfileResponse.model_validate(profile)


@router.patch("/{client_id}/tax-profile", response_model=TaxProfileResponse)
def update_tax_profile(
    client_id: int,
    request: TaxProfileUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    if request.vat_type is not None:
        try:
            VatType(request.vat_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid vat_type: {request.vat_type}",
            )
    service = ClientTaxProfileService(db)
    try:
        update_data = request.model_dump(exclude_unset=True)
        profile = service.update_profile(client_id, **update_data)
        return TaxProfileResponse.model_validate(profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
