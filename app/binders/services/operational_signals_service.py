from datetime import date
from typing import Optional

from app.binders.services.operational_signals_builder import build_client_operational_signals
from app.binders.services.signals_service import SignalsService


class OperationalSignalsService(SignalsService):
    """
    Legacy "operational signals" payload (documents API + tests).

    Payload shape:
        {
            "client_id": int,
            "missing_documents": [str],
            "binders_nearing_sla": [{"binder_id", "binder_number", "days_remaining"}],
            "binders_overdue": [{"binder_id", "binder_number", "days_overdue"}],
        }
    """

    def get_client_signals(
        self,
        client_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        if reference_date is None:
            reference_date = date.today()
        return build_client_operational_signals(
            self.document_service,
            self.binder_repo,
            client_id=client_id,
            reference_date=reference_date,
        )
