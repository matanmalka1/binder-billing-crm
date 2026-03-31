from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.permanent_documents.models.permanent_document import (
    DocumentScope,
    DocumentStatus,
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
            uploaded_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 500))
            status = rng.choices(
                [DocumentStatus.PENDING, DocumentStatus.RECEIVED, DocumentStatus.APPROVED, DocumentStatus.REJECTED],
                weights=[10, 20, 60, 10],
                k=1,
            )[0]
            approved_by = None
            approved_at = None
            if status == DocumentStatus.APPROVED and rng.random() < 0.7:
                approved_by = rng.choice(users).id
                approved_at = uploaded_at + timedelta(days=rng.randint(1, 30))

            document = PermanentDocument(
                client_id=client.id,
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
                is_present=rng.random() > 0.05,
                notes=rng.choice([None, "סריקה באיכות טובה", "נדרש דף ספח", "עודכן לפי מסמך חדש"]),
                uploaded_by=rng.choice(users).id,
                uploaded_at=uploaded_at,
                approved_by=approved_by,
                approved_at=approved_at,
                rejected_by=rng.choice(users).id if status == DocumentStatus.REJECTED else None,
                rejected_at=uploaded_at + timedelta(days=rng.randint(1, 10))
                if status == DocumentStatus.REJECTED
                else None,
            )
            db.add(document)
            documents.append(document)

        for business in businesses_by_client_id.get(client.id, []):
            if rng.random() > 0.6:
                continue
            uploaded_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 500))
            status = rng.choices(
                [DocumentStatus.PENDING, DocumentStatus.RECEIVED, DocumentStatus.APPROVED, DocumentStatus.REJECTED],
                weights=[10, 20, 60, 10],
                k=1,
            )[0]
            approved_by = None
            approved_at = None
            if status == DocumentStatus.APPROVED and rng.random() < 0.7:
                approved_by = rng.choice(users).id
                approved_at = uploaded_at + timedelta(days=rng.randint(1, 30))

            document = PermanentDocument(
                client_id=client.id,
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
                is_present=rng.random() > 0.05,
                notes=rng.choice([None, "מסמך מסווג להוצאות", "שייך לשנת המס האחרונה", "נשלח על ידי הלקוח"]),
                uploaded_by=rng.choice(users).id,
                uploaded_at=uploaded_at,
                approved_by=approved_by,
                approved_at=approved_at,
                rejected_by=rng.choice(users).id if status == DocumentStatus.REJECTED else None,
                rejected_at=uploaded_at + timedelta(days=rng.randint(1, 10))
                if status == DocumentStatus.REJECTED
                else None,
            )
            db.add(document)
            documents.append(document)
    db.flush()
    return documents
