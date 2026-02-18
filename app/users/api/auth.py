from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response, status

from app.users.api.deps import DBSession
from app.users.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.users.services.auth_service import AuthService
from app.config import config

router = APIRouter(prefix="/auth", tags=["auth"])


COOKIE_NAME = "access_token"
COOKIE_SAMESITE = "lax"


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: DBSession, response: Response):
    """Authenticate user and return user info (JWT is set as HttpOnly cookie)."""
    auth_service = AuthService(db)

    user = auth_service.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    ttl_hours = config.JWT_TTL_HOURS
    # Extend session if user selected "remember me" (double the TTL)
    if request.remember_me:
        ttl_hours = config.JWT_TTL_HOURS * 2

    token = auth_service.generate_token(user, ttl_hours=ttl_hours)

    # Set HttpOnly cookie for token-based auth (sent automatically by browser)
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
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            role=user.role.value,
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    """
    Clear the auth cookie to end the session on the client.
    Token remains valid server-side until expiration, but the browser
    will no longer send it after the cookie is deleted.
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=config.APP_ENV == "production",
        samesite=COOKIE_SAMESITE,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
