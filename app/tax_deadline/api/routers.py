"""Tax deadline API router aggregating sub-routers."""

from fastapi import APIRouter

from app.tax_deadline.api.deadline_generate import router as deadline_generate_router
from app.tax_deadline.api.deadline_grouped import router as deadline_grouped_router
from app.tax_deadline.api.tax_deadline import router as tax_deadline_router
from app.tax_deadline.api.tax_deadline_queries import router as tax_deadline_queries_router

router = APIRouter()
router.include_router(deadline_grouped_router)
router.include_router(tax_deadline_router)
router.include_router(deadline_generate_router)
router.include_router(tax_deadline_queries_router)

__all__ = ["router"]
