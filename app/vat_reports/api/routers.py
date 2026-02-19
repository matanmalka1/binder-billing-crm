"""VAT Reports API router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.vat_reports.api.routes_data_entry import router as data_entry_router
from app.vat_reports.api.routes_filing import router as filing_router
from app.vat_reports.api.routes_intake import router as intake_router
from app.vat_reports.api.routes_queries import router as queries_router

router = APIRouter()
router.include_router(intake_router)
router.include_router(data_entry_router)
router.include_router(filing_router)
router.include_router(queries_router)

__all__ = ["router"]
