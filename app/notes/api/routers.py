from fastapi import APIRouter

from app.notes.api.entity_notes import router as client_notes_router
from app.notes.api.business_notes import router as business_notes_router

router = APIRouter()
router.include_router(client_notes_router)
router.include_router(business_notes_router)
