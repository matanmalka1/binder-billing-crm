"""Annual reports API router aggregating sub-routers."""

from fastapi import APIRouter

from app.annual_reports.api.annual_report_annex import router as annex_router
from app.annual_reports.api.annual_report_business import businesses_router
from app.annual_reports.api.annual_report_charges import router as charges_router
from app.annual_reports.api.annual_report_create_read import router as create_read_router
from app.annual_reports.api.annual_report_detail import router as detail_router
from app.annual_reports.api.annual_report_financials import router as financials_router
from app.annual_reports.api.annual_report_kanban import router as kanban_router
from app.annual_reports.api.annual_report_schedule import router as schedule_router
from app.annual_reports.api.annual_report_season import season_router
from app.annual_reports.api.annual_report_status import router as status_router
from app.annual_reports.api.annual_report_tax import router as tax_router
from app.annual_reports.api.routes_export import router as export_router

router = APIRouter()
router.include_router(annex_router)
router.include_router(detail_router)
router.include_router(financials_router)
router.include_router(create_read_router)
router.include_router(schedule_router)
router.include_router(kanban_router)
router.include_router(status_router)
router.include_router(businesses_router)
router.include_router(season_router)
router.include_router(export_router)
router.include_router(tax_router)
router.include_router(charges_router)

__all__ = ["router"]
