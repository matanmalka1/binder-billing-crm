"""Users API router aggregating sub-routers."""

from fastapi import APIRouter

from app.users.api.auth import router as auth_router
from app.users.api.users import router as users_router
from app.users.api.users_audit import router as users_audit_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_audit_router)
router.include_router(users_router)

__all__ = ["router"]
