"""Correspondence API router aggregating sub-routers."""

from fastapi import APIRouter

from app.correspondence.api.correspondence import business_router, client_router

router = APIRouter()
router.include_router(business_router)
router.include_router(client_router)

__all__ = ["router"]