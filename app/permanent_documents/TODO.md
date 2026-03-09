## [P2] 6.4 — סינון לפי שנת מס (Filter by Tax Year)
**Status:** MISSING
**Gap:** `PermanentDocument` model has no `tax_year` field; documents cannot be filtered or scoped by tax year.
**Files to touch:**
- `app/permanent_documents/models/permanent_document.py` — add `tax_year: Integer, nullable` column
- `app/permanent_documents/schemas/permanent_document.py` — add `tax_year: Optional[int]` to create/update/response schemas
- `app/permanent_documents/repositories/permanent_document_repository.py` — add optional `tax_year` filter to `list_by_client()`
- `app/permanent_documents/api/permanent_documents.py` — add `?tax_year=` query param to list endpoint
- `alembic/versions/` — migration for new column
**Acceptance criteria:** `GET /documents/client/{id}?tax_year=2024` returns only documents tagged to that year; documents without `tax_year` are returned when param is omitted.

---

## [P2] 6.7 — קישור מסמך-ניכוי (Document-Deduction Link)
**Status:** MISSING
**Gap:** No `supporting_document_ref` or `document_id` foreign key exists on any expense/deduction model; documents cannot be linked to specific deductions.
**Files to touch:**
- `app/annual_reports/models/annual_report_detail.py` — add `supporting_document_id: ForeignKey(permanent_documents.id), nullable` per expense line (or handle in a join table if multi-document)
- `app/annual_reports/schemas/annual_report_detail.py` — add `supporting_document_id: Optional[UUID]` to expense create/update/response
- `app/annual_reports/api/annual_report_create_read.py` — ensure document link is accepted and returned
**Acceptance criteria:** Expense/deduction lines accept `supporting_document_id`; detail response resolves the linked document filename and URL.

---

## [P3] 6.3 — קטגוריות מסמכים נוספות (Additional Document Categories)
**Status:** PARTIAL
**Gap:** `DocumentType` enum has only 3 values (ID_COPY, POWER_OF_ATTORNEY, ENGAGEMENT_AGREEMENT); tax-domain categories (TAX_FORM, RECEIPT, INVOICE, BANK_APPROVAL) are absent.
**Files to touch:**
- `app/permanent_documents/models/permanent_document.py` — extend `DocumentType` enum with `TAX_FORM`, `RECEIPT`, `INVOICE`, `BANK_APPROVAL`, `OTHER`
- `alembic/versions/` — migration if enum is DB-native (PostgreSQL requires ALTER TYPE)
**Acceptance criteria:** Upload endpoint accepts all new category values; list endpoint returns the correct `document_type` label for each.
