"""Notification API router aggregating sub-routers."""

from fastapi import APIRouter

from app.notification.api.notifications import advisor_router, router as notifications_router

router = APIRouter()
router.include_router(notifications_router)
router.include_router(advisor_router)

__all__ = ["router"]
