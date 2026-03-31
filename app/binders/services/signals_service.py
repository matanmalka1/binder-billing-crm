from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.constants import SignalType
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository
from app.binders.services.operational_signals_builder import build_client_operational_signals
from app.charge.models.charge import ChargeStatus
from app.binders.models.binder import BinderStatus
from app.notification.models.notification import Notification
from app.binders.services.constants import IDLE_THRESHOLD_DAYS


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
        from app.permanent_documents.services.permanent_document_service import (
            PermanentDocumentService,
        )
        self.document_service = PermanentDocumentService(db)

    def compute_binder_signals(
        self,
        binder: Binder,
        reference_date: Optional[date] = None,
    ) -> list[str]:
        """Compute signals for a single binder. Returns list of signal type values."""
        if reference_date is None:
            reference_date = date.today()

        signals = []

        if binder.status == BinderStatus.READY_FOR_PICKUP:
            signals.append(SignalType.READY_FOR_PICKUP.value)

        if self.is_idle_binder(binder, reference_date):
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

        Note: missing_documents and unpaid_charges are business-level concepts
        that require a business_id. This method returns empty/False for them
        unless called with a specific business context.
        """
        if reference_date is None:
            reference_date = date.today()

        binders = self.binder_repo.list_active(client_id=client_id)
        binder_signals = {}
        for binder in binders:
            signals = self.compute_binder_signals(binder, reference_date)
            if signals:
                binder_signals[binder.id] = signals

        return {
            "missing_documents": [],
            "unpaid_charges": False,
            "binder_signals": binder_signals,
        }

    def is_idle_binder(
        self,
        binder: Binder,
        reference_date: Optional[date] = None,
    ) -> bool:
        if reference_date is None:
            reference_date = date.today()

        if binder.status != BinderStatus.IN_OFFICE:
            return False

        days_since_start = (reference_date - binder.period_start).days
        if days_since_start < IDLE_THRESHOLD_DAYS:
            return False

        return not self._has_recent_notification_activity(binder, reference_date)

    def _has_recent_notification_activity(
        self,
        binder: Binder,
        reference_date: date,
    ) -> bool:
        threshold_date = reference_date - timedelta(days=IDLE_THRESHOLD_DAYS)
        result = (
            self.db.query(Notification)
            .filter(
                Notification.binder_id == binder.id,
                Notification.created_at >= threshold_date,
            )
            .limit(1)
            .first()
        )
        return result is not None

    def compute_business_signals(
        self,
        business_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        """
        Compute signals for a business (charges, documents).
        Binder signals are computed at client level — not included here.
        """
        if reference_date is None:
            reference_date = date.today()

        missing_docs = self.document_service.get_missing_document_types(business_id)

        unpaid = self.charge_repo.count_charges(
            business_id=business_id,
            status=ChargeStatus.ISSUED.value,
        ) > 0

        return {
            "missing_documents": list(missing_docs),
            "unpaid_charges": unpaid,
            "binder_signals": {},
        }

    def compute_business_operational_signals(
        self,
        business_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        if reference_date is None:
            reference_date = date.today()
        return build_client_operational_signals(
            self.document_service,
            self.binder_repo,
            business_id=business_id,
            reference_date=reference_date,
        )
