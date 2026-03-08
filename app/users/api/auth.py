from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response, status

from app.users.api.deps import CurrentUser, DBSession
from app.users.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.users.services.auth_service import AuthService
from app.config import config

router = APIRouter(prefix="/auth", tags=["auth"])


COOKIE_NAME = "access_token"
COOKIE_SAMESITE = "none" if config.APP_ENV == "production" else "lax"


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: DBSession, response: Response):
    """Authenticate user and return user info (JWT is set as HttpOnly cookie)."""
    auth_service = AuthService(db)

    user = auth_service.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="אימייל או סיסמה שגויים",
        )

    ttl_hours = config.JWT_TTL_HOURS
    if request.remember_me:
        ttl_hours = config.JWT_TTL_HOURS * 2

    token = auth_service.generate_token(user, ttl_hours=ttl_hours)

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.APP_ENV == "production",
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=int(timedelta(hours=ttl_hours).total_seconds()),
    )

    return LoginResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            role=user.role.value,
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: DBSession, current_user: CurrentUser, response: Response):
    """
    Invalidate the user's token server-side and clear the auth cookie.

    Bumps token_version on the User record so all active tokens — including
    any Bearer token held outside the cookie — are rejected immediately.
    """
    auth_service = AuthService(db)
    auth_service.logout(current_user)

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=config.APP_ENV == "production",
        samesite=COOKIE_SAMESITE,
    )
