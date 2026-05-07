from fastapi import APIRouter

from app.tax_calendar.api.groups import router as groups_router

router = APIRouter()
router.include_router(groups_router)

__all__ = ["router"]
