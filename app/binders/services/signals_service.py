from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.services.operational_signals_builder import build_client_operational_signals


class SignalsService:
    """
    Compute operational signals for UX.

    Signals are:
    - Derived dynamically (NOT persisted)
    - Advisory only (non-blocking)
    - Internal UX indicators
    """

    def __init__(self, db: Session):
        self.db = db
        from app.permanent_documents.services.permanent_document_service import (
            PermanentDocumentService,
        )
        self.document_service = PermanentDocumentService(db)

    def compute_business_operational_signals(
        self,
        business_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        if reference_date is None:
            reference_date = date.today()
        return build_client_operational_signals(
            self.document_service,
            business_id=business_id,
        )
