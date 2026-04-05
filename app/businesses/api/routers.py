"""Businesses API router aggregating sub-routers."""

from fastapi import APIRouter

from app.businesses.api.business_binders_router import router as business_binders_router
from app.businesses.api.business_status_card_router import router as business_status_card_router
from app.businesses.api.business_tax_profile_router import router as business_tax_profile_router
from app.businesses.api.businesses import businesses_router
from app.businesses.api.client_businesses_router import client_businesses_router

router = APIRouter()
router.include_router(business_status_card_router)
router.include_router(business_binders_router)
router.include_router(business_tax_profile_router)
router.include_router(client_businesses_router)
router.include_router(businesses_router)

__all__ = ["router"]
