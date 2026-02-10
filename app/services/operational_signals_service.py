from datetime import date
from typing import Optional

from app.services.signals_service import SignalsService
from app.services.sla_service import SLAService


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

