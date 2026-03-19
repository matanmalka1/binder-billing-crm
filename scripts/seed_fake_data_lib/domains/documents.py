from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.permanent_documents.models.permanent_document import (
    DocumentScope,
    DocumentType,
    PermanentDocument,
)


def create_documents(db, rng: Random, clients, businesses, users):
    documents: list[PermanentDocument] = []
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)

    for client in clients:
        docs = [DocumentType.ID_COPY, DocumentType.POWER_OF_ATTORNEY]
        if rng.random() < 0.8:
            docs.append(DocumentType.ENGAGEMENT_AGREEMENT)
        for doc_type in docs:
            document = PermanentDocument(
                client_id=client.id,
                business_id=None,
                scope=DocumentScope.CLIENT,
                document_type=doc_type,
                storage_key=(
                    f"clients/{client.id}/"
                    f"{doc_type.value}_{rng.randint(1000, 9999)}.pdf"
                ),
                is_present=rng.random() > 0.05,
                uploaded_by=rng.choice(users).id,
                uploaded_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 500)),
            )
            db.add(document)
            documents.append(document)

        for business in businesses_by_client_id.get(client.id, []):
            if rng.random() > 0.6:
                continue
            document = PermanentDocument(
                client_id=client.id,
                business_id=business.id,
                scope=DocumentScope.BUSINESS,
                document_type=rng.choice([DocumentType.INVOICE_DOC, DocumentType.RECEIPT, DocumentType.TAX_FORM]),
                storage_key=(
                    f"clients/{client.id}/businesses/{business.id}/"
                    f"doc_{rng.randint(1000, 9999)}.pdf"
                ),
                is_present=rng.random() > 0.05,
                uploaded_by=rng.choice(users).id,
                uploaded_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 500)),
            )
            db.add(document)
            documents.append(document)
    db.flush()
    return documents
