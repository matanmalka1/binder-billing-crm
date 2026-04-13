from datetime import date


def build_client_operational_signals(
    document_service,
    business_id: int,
) -> dict:
    missing_docs = document_service.get_missing_document_types(business_id)

    return {
        "business_id": business_id,
        "missing_documents": list(missing_docs),
    }
