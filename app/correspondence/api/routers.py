"""Correspondence API router aggregating sub-routers."""

from fastapi import APIRouter

from app.correspondence.api.correspondence import router as correspondence_router

router = APIRouter()
router.include_router(correspondence_router)

__all__ = ["router"]
