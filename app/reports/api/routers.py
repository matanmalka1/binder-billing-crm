"""Reports API router aggregating sub-routers."""

from fastapi import APIRouter

from app.reports.api.reports import router as reports_router

router = APIRouter()
router.include_router(reports_router)

__all__ = ["router"]
