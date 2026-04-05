"""Timeline API router aggregating sub-routers."""

from fastapi import APIRouter

from app.timeline.api.timeline import router as timeline_router

router = APIRouter()
router.include_router(timeline_router)

__all__ = ["router"]
