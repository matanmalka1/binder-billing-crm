from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.permanent_documents.models.permanent_document import DocumentType, PermanentDocument


def create_documents(db, rng: Random, clients, users):
    for client in clients:
        docs = [DocumentType.ID_COPY, DocumentType.POWER_OF_ATTORNEY]
        if rng.random() < 0.8:
            docs.append(DocumentType.ENGAGEMENT_AGREEMENT)
        for doc_type in docs:
            document = PermanentDocument(
                client_id=client.id,
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
    db.flush()
