from fastapi import APIRouter, Depends, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
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
    """Generate all tax deadlines for a client and year. Skips existing (idempotent)."""
    service = DeadlineGeneratorService(db)
    created_count = service.generate_all(request.client_id, request.year)
    return GenerateDeadlinesResponse(created_count=created_count)
