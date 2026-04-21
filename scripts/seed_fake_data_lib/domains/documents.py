from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.permanent_documents.models.permanent_document import (
    DocumentScope,
    DocumentStatus,
    DocumentType,
    PermanentDocument,
)
from ..demo_catalog import DOCUMENT_NOTES


def create_documents(db, rng: Random, clients, businesses, users):
    documents: list[PermanentDocument] = []
    now = datetime.now(UTC)
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)

    for client in clients:
        docs = [DocumentType.ID_COPY, DocumentType.POWER_OF_ATTORNEY]
        if rng.random() < 0.8:
            docs.append(DocumentType.ENGAGEMENT_AGREEMENT)
        for doc_type in docs:
            uploaded_at = now - timedelta(days=rng.randint(0, 500))
            status = rng.choices(
                [DocumentStatus.PENDING, DocumentStatus.RECEIVED, DocumentStatus.APPROVED, DocumentStatus.REJECTED],
                weights=[10, 20, 60, 10],
                k=1,
            )[0]
            is_present = rng.random() > 0.05
            if not is_present and status in (DocumentStatus.APPROVED, DocumentStatus.RECEIVED):
                status = DocumentStatus.PENDING
            approved_by = None
            approved_at = None
            if status == DocumentStatus.APPROVED and is_present and rng.random() < 0.7:
                approved_by = rng.choice(users).id
                approved_at = min(now, uploaded_at + timedelta(days=rng.randint(1, 30)))
            rejected_at = None
            rejected_by = None
            if status == DocumentStatus.REJECTED:
                rejected_by = rng.choice(users).id
                rejected_at = min(now, uploaded_at + timedelta(days=rng.randint(1, 10)))

            document = PermanentDocument(
                client_record_id=client.id,
                business_id=None,
                scope=DocumentScope.CLIENT,
                document_type=doc_type,
                storage_key=(
                    f"clients/{client.id}/"
                    f"{doc_type.value}_{rng.randint(1000, 9999)}.pdf"
                ),
                original_filename=f"{doc_type.value}.pdf",
                file_size_bytes=rng.randint(50000, 500000),
                mime_type="application/pdf",
                tax_year=None,
                status=status,
                is_present=is_present,
                notes=rng.choice(DOCUMENT_NOTES),
                uploaded_by=rng.choice(users).id,
                uploaded_at=uploaded_at,
                approved_by=approved_by,
                approved_at=approved_at,
                rejected_by=rejected_by,
                rejected_at=rejected_at,
            )
            document.client_id = client.id
            db.add(document)
            documents.append(document)

        client_businesses = businesses_by_client_id.get(client.id, [])
        remaining_business_doc_slots = max(0, 4 - len(docs))
        if remaining_business_doc_slots <= 0:
            continue

        selected_businesses = rng.sample(
            client_businesses,
            k=min(remaining_business_doc_slots, len(client_businesses)),
        )
        for business in selected_businesses:
            uploaded_at = now - timedelta(days=rng.randint(0, 500))
            status = rng.choices(
                [DocumentStatus.PENDING, DocumentStatus.RECEIVED, DocumentStatus.APPROVED, DocumentStatus.REJECTED],
                weights=[10, 20, 60, 10],
                k=1,
            )[0]
            is_present = rng.random() > 0.05
            if not is_present and status in (DocumentStatus.APPROVED, DocumentStatus.RECEIVED):
                status = DocumentStatus.PENDING
            approved_by = None
            approved_at = None
            if status == DocumentStatus.APPROVED and is_present and rng.random() < 0.7:
                approved_by = rng.choice(users).id
                approved_at = min(now, uploaded_at + timedelta(days=rng.randint(1, 30)))
            rejected_at = None
            rejected_by = None
            if status == DocumentStatus.REJECTED:
                rejected_by = rng.choice(users).id
                rejected_at = min(now, uploaded_at + timedelta(days=rng.randint(1, 10)))

            document = PermanentDocument(
                client_record_id=client.id,
                business_id=business.id,
                scope=DocumentScope.BUSINESS,
                document_type=rng.choice([DocumentType.INVOICE_DOC, DocumentType.RECEIPT, DocumentType.TAX_FORM]),
                storage_key=(
                    f"clients/{client.id}/businesses/{business.id}/"
                    f"doc_{rng.randint(1000, 9999)}.pdf"
                ),
                original_filename=f"document_{rng.randint(1000, 9999)}.pdf",
                file_size_bytes=rng.randint(50000, 500000),
                mime_type="application/pdf",
                tax_year=rng.choice([uploaded_at.year, uploaded_at.year - 1, None]),
                status=status,
                is_present=is_present,
                notes=rng.choice(DOCUMENT_NOTES),
                uploaded_by=rng.choice(users).id,
                uploaded_at=uploaded_at,
                approved_by=approved_by,
                approved_at=approved_at,
                rejected_by=rejected_by,
                rejected_at=rejected_at,
            )
            document.client_id = client.id
            db.add(document)
            documents.append(document)
    db.flush()
    return documents
