from datetime import date
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Binder
from app.repositories import BinderRepository, ChargeRepository, ClientRepository
from app.services.permanent_document_service import PermanentDocumentService
from app.services.sla_service import SLAService
from app.services.work_state_service import WorkStateService


class SignalType(str, PyEnum):
    """Operational signal types (internal, non-blocking)."""
    
    MISSING_DOCUMENTS = "missing_permanent_documents"
    NEAR_SLA = "near_sla"
    OVERDUE = "overdue"
    READY_FOR_PICKUP = "ready_for_pickup"
    UNPAID_CHARGES = "unpaid_charges"
    IDLE_BINDER = "idle_binder"


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
        self.client_repo = ClientRepository(db)
        self.binder_repo = BinderRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.document_service = PermanentDocumentService(db)

    def compute_binder_signals(
        self,
        binder: Binder,
        reference_date: Optional[date] = None,
    ) -> list[str]:
        """
        Compute signals for a single binder.
        
        Returns list of signal type values.
        """
        if reference_date is None:
            reference_date = date.today()

        signals = []

        # Overdue signal
        if SLAService.is_overdue(binder, reference_date):
            signals.append(SignalType.OVERDUE.value)

        # Near SLA signal
        elif SLAService.is_approaching_sla(binder, reference_date):
            signals.append(SignalType.NEAR_SLA.value)

        # Ready for pickup signal
        from app.models import BinderStatus
        if binder.status == BinderStatus.READY_FOR_PICKUP:
            signals.append(SignalType.READY_FOR_PICKUP.value)

        # Idle binder signal
        if WorkStateService.is_idle(binder, reference_date):
            signals.append(SignalType.IDLE_BINDER.value)

        return signals

    def compute_client_signals(
        self,
        client_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        """
        Compute all signals for a client.
        
        Returns:
            {
                "missing_documents": [...],
                "unpaid_charges": bool,
                "binder_signals": {binder_id: [signals]}
            }
        """
        if reference_date is None:
            reference_date = date.today()

        # Missing documents signal
        missing_docs = self.document_service.get_missing_document_types(client_id)

        # Unpaid charges signal
        from app.models import ChargeStatus
        unpaid = self.charge_repo.count_charges(
            client_id=client_id,
            status=ChargeStatus.ISSUED.value,
        ) > 0

        # Binder signals
        binders = self.binder_repo.list_active(client_id=client_id)
        binder_signals = {}
        for binder in binders:
            signals = self.compute_binder_signals(binder, reference_date)
            if signals:
                binder_signals[binder.id] = signals

        return {
            "missing_documents": [dt.value for dt in missing_docs],
            "unpaid_charges": unpaid,
            "binder_signals": binder_signals,
        }

    def compute_client_operational_signals(
        self,
        client_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        """
        Compute legacy "operational signals" response for documents API.

        This preserves the `/documents/client/{client_id}/signals` payload shape:
            {
                "client_id": int,
                "missing_documents": [str],
                "binders_nearing_sla": [{"binder_id", "binder_number", "days_remaining"}],
                "binders_overdue": [{"binder_id", "binder_number", "days_overdue"}],
            }
        """
        if reference_date is None:
            reference_date = date.today()

        missing_docs = self.document_service.get_missing_document_types(client_id)
        binders = self.binder_repo.list_active(client_id=client_id)

        nearing_sla: list[dict] = []
        overdue: list[dict] = []

        for binder in binders:
            if SLAService.is_overdue(binder, reference_date):
                overdue.append(
                    {
                        "binder_id": binder.id,
                        "binder_number": binder.binder_number,
                        "days_overdue": SLAService.days_overdue(binder, reference_date),
                    }
                )
            elif SLAService.is_approaching_sla(binder, reference_date):
                nearing_sla.append(
                    {
                        "binder_id": binder.id,
                        "binder_number": binder.binder_number,
                        "days_remaining": SLAService.days_remaining(binder, reference_date),
                    }
                )

        return {
            "client_id": client_id,
            "missing_documents": [dt.value for dt in missing_docs],
            "binders_nearing_sla": nearing_sla,
            "binders_overdue": overdue,
        }
