
## [P3] 6.3 — קטגוריות מסמכים נוספות (Additional Document Categories)
**Status:** PARTIAL
**Gap:** `DocumentType` enum has only 3 values (ID_COPY, POWER_OF_ATTORNEY, ENGAGEMENT_AGREEMENT); tax-domain categories (TAX_FORM, RECEIPT, INVOICE, BANK_APPROVAL) are absent.
**Files to touch:**
- `app/permanent_documents/models/permanent_document.py` — extend `DocumentType` enum with `TAX_FORM`, `RECEIPT`, `INVOICE`, `BANK_APPROVAL`, `OTHER`
- `alembic/versions/` — migration if enum is DB-native (PostgreSQL requires ALTER TYPE)
**Acceptance criteria:** Upload endpoint accepts all new category values; list endpoint returns the correct `document_type` label for each.
