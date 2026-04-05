"""Dashboard API router aggregating sub-routers."""

from fastapi import APIRouter

from app.dashboard.api.dashboard import router as dashboard_router
from app.dashboard.api.dashboard_extended import router as dashboard_extended_router
from app.dashboard.api.dashboard_overview import router as dashboard_overview_router
from app.dashboard.api.dashboard_tax import router as dashboard_tax_router

router = APIRouter()
router.include_router(dashboard_tax_router)
router.include_router(dashboard_router)
router.include_router(dashboard_overview_router)
router.include_router(dashboard_extended_router)

__all__ = ["router"]
