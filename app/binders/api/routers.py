"""Binders API router aggregating sub-routers."""

from fastapi import APIRouter

from app.binders.api.binders import router as binders_router
from app.binders.api.binders_history import router as binders_history_router
from app.binders.api.binders_operations import router as binders_operations_router

router = APIRouter()
router.include_router(binders_operations_router)
router.include_router(binders_router)
router.include_router(binders_history_router)

__all__ = ["router"]
