"""Businesses API router aggregating sub-routers."""

from fastapi import APIRouter

from app.businesses.api.client_businesses_router import client_businesses_router

router = APIRouter()
router.include_router(client_businesses_router)

__all__ = ["router"]
