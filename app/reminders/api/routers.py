from __future__ import annotations

from fastapi import APIRouter

from app.reminders.api.routes_cancel import cancel_router
from app.reminders.api.routes_create import create_router
from app.reminders.api.routes_get import get_router
from app.reminders.api.routes_list import list_router
from app.reminders.api.routes_mark_sent import mark_sent_router


router = APIRouter(prefix="/reminders", tags=["reminders"])
router.include_router(list_router)
router.include_router(get_router)
router.include_router(create_router)
router.include_router(cancel_router)
router.include_router(mark_sent_router)
