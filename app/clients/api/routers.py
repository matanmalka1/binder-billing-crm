"""Clients API router aggregating sub-routers."""

from fastapi import APIRouter

from app.clients.api.clients import router as clients_router
from app.clients.api.clients_excel import router as clients_excel_router

router = APIRouter()
router.include_router(clients_excel_router)
router.include_router(clients_router)

__all__ = ["router"]
