from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.permanent_documents.models.permanent_document import (
    DocumentScope,
    DocumentStatus,
    DocumentType,
    PermanentDocument,
)
from ..realistic_seed_text import DOCUMENT_TYPE_DETAILS


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
        if rng.random() < 0.55:
            docs.append(DocumentType.BANK_APPROVAL)
        for doc_type in docs:
            doc_label, filename = DOCUMENT_TYPE_DETAILS[doc_type]
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
                original_filename=filename,
                file_size_bytes=rng.randint(50000, 500000),
                mime_type="application/pdf",
                tax_year=None,
                status=status,
                is_present=is_present,
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

            doc_type = rng.choice([
                DocumentType.INVOICE_DOC,
                DocumentType.RECEIPT,
                DocumentType.TAX_FORM,
                DocumentType.WITHHOLDING_CERTIFICATE,
                DocumentType.NII_APPROVAL,
            ])
            doc_label, filename = DOCUMENT_TYPE_DETAILS[doc_type]
            document = PermanentDocument(
                client_record_id=client.id,
                business_id=business.id,
                scope=DocumentScope.BUSINESS,
                document_type=doc_type,
                storage_key=(
                    f"clients/{client.id}/businesses/{business.id}/"
                    f"doc_{rng.randint(1000, 9999)}.pdf"
                ),
                original_filename=f"{business.business_name}_{filename}",
                file_size_bytes=rng.randint(50000, 500000),
                mime_type="application/pdf",
                tax_year=rng.choice([uploaded_at.year, uploaded_at.year - 1, None]),
                status=status,
                is_present=is_present,
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
