from fastapi import APIRouter, HTTPException, status

from app.api.deps import DBSession
from app.schemas import LoginRequest, LoginResponse, UserResponse
from app.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: DBSession):
    """Authenticate user and return JWT token."""
    auth_service = AuthService(db)

    user = auth_service.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = auth_service.generate_token(user)

    return LoginResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            role=user.role.value,
        ).model_dump(),
    )