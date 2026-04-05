"""Search API router aggregating sub-routers."""

from fastapi import APIRouter

from app.search.api.search import router as search_router

router = APIRouter()
router.include_router(search_router)

__all__ = ["router"]
