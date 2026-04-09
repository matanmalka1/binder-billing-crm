from fastapi import APIRouter, Depends, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.repositories.business_repository import BusinessRepository
from app.core.exceptions import AppError
from app.tax_deadline.schemas.tax_deadline import GenerateDeadlinesRequest, GenerateDeadlinesResponse
from app.tax_deadline.services.deadline_generator import DeadlineGeneratorService

router = APIRouter(
    prefix="/tax-deadlines",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.post(
    "/generate",
    response_model=GenerateDeadlinesResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_deadlines(
    request: GenerateDeadlinesRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Generate all tax deadlines for a client and year. Skips existing (idempotent).

    Accepts client_id directly, or business_id as a deprecated bridge (resolved to client_id).
    """
    client_id = request.client_id
    if client_id is None:
        if request.business_id is None:
            raise AppError("יש לספק client_id או business_id", "TAX_DEADLINE.MISSING_IDENTIFIER")
        business = BusinessRepository(db).get_by_id(request.business_id)
        if not business:
            raise AppError(f"עסק {request.business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        client_id = business.client_id

    service = DeadlineGeneratorService(db)
    created_count = service.generate_all(client_id, request.year)
    return GenerateDeadlinesResponse(created_count=created_count)
