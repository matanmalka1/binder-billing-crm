from datetime import date


def build_client_operational_signals(
    document_service,
    binder_repo,
    client_id: int,
    reference_date: date,
) -> dict:
    missing_docs = document_service.get_missing_document_types(client_id)

    return {
        "client_id": client_id,
        "missing_documents": [dt.value for dt in missing_docs],
    }
