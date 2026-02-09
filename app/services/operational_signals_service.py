from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Binder
from app.repositories import BinderRepository
from app.services.permanent_document_service import PermanentDocumentService
from app.services.sla_service import SLAService


class OperationalSignalsService:
    """
    Operational signals service for Sprint 4.
    
    Provides advisory (non-blocking) indicators:
    - Missing permanent documents
    - Binder nearing SLA
    - Binder overdue
    """

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.document_service = PermanentDocumentService(db)

    def get_client_signals(self, client_id: int, reference_date: Optional[date] = None) -> dict:
        """
        Get operational signals for a client.
        
        Returns advisory indicators only (non-blocking).
        """
        if reference_date is None:
            reference_date = date.today()

        # Missing documents signal
        missing_documents = self.document_service.get_missing_document_types(client_id)

        # Binder signals
        binders = self.binder_repo.list_active(client_id=client_id)
        
        nearing_sla = []
        overdue = []

        for binder in binders:
            if SLAService.is_overdue(binder, reference_date):
                overdue.append({
                    "binder_id": binder.id,
                    "binder_number": binder.binder_number,
                    "days_overdue": SLAService.days_overdue(binder, reference_date),
                })
            else:
                if SLAService.is_approaching_sla(binder, reference_date):
                    nearing_sla.append({
                        "binder_id": binder.id,
                        "binder_number": binder.binder_number,
                        "days_remaining": SLAService.days_remaining(binder, reference_date),
                    })

        return {
            "client_id": client_id,
            "missing_documents": [dt.value for dt in missing_documents],
            "binders_nearing_sla": nearing_sla,
            "binders_overdue": overdue,
        }
