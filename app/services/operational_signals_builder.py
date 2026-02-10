from datetime import date

from app.services.sla_service import SLAService


def build_client_operational_signals(
    document_service,
    binder_repo,
    client_id: int,
    reference_date: date,
) -> dict:
    missing_docs = document_service.get_missing_document_types(client_id)
    binders = binder_repo.list_active(client_id=client_id)

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
