"""Facade to preserve original router import path after split."""

from fastapi import APIRouter

from app.binders.api import binders_list_get, binders_receive_return

router = APIRouter()
router.include_router(binders_receive_return.router)
router.include_router(binders_list_get.router)

__all__ = ["router"]
