# Permanent Documents Module

> Last audited: 2026-03-22 (post-refactor sync).

Manages client permanent documents (upload, versioning, status actions, retrieval, and advisory missing-doc signals) used across operational and annual-report workflows.

## Scope

This module provides:
- Permanent-document upload and retrieval
- Business document listing with optional tax-year filtering
- Document replacement and soft delete
- Document workflow actions (approve/reject/update notes)
- Version history queries by document type/year
- Annual-report scoped document listing
- Operational missing-document signals per business
- Role-based API access

## Domain Model

`PermanentDocument` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required — denormalized for fast queries)
- `business_id` (FK -> `businesses.id`, nullable — NULL for CLIENT-scoped documents)
- `scope` (enum: `client` | `business`, required)
- `document_type` (enum, required)
- `storage_key` (required)
- `tax_year` (optional)
- `is_present` (default `true`)
- `is_deleted` (default `false`)
- `uploaded_by` (FK -> `users.id`, required)
- `uploaded_at`
- `version` (default `1`)
- `superseded_by` (self-reference FK to newer version)
- `status` (enum, default `pending`)
- `annual_report_id` (optional FK -> `annual_reports.id`)
- `original_filename`, `file_size_bytes`, `mime_type`, `notes` (optional metadata)
- `approved_by`, `approved_at`
- `rejected_by`, `rejected_at`

Document scope enum values:
- `client` — identity documents belonging to the person (id_copy, power_of_attorney, engagement_agreement). `business_id` is NULL.
- `business` — business-specific documents. `business_id` is required.

A DB-level `CheckConstraint` enforces: `scope = 'business'` requires `business_id IS NOT NULL`.

Document type enum values:
- `id_copy`
- `power_of_attorney`
- `engagement_agreement`
- `tax_form`
- `receipt`
- `invoice_doc`
- `bank_approval`
- `withholding_certificate`
- `nii_approval`
- `other`

Document status enum values:
- `pending`
- `received`
- `approved`
- `rejected`

Implementation references:
- Model: `app/permanent_documents/models/permanent_document.py`
- Schemas: `app/permanent_documents/schemas/permanent_document.py`
- Repositories: `app/permanent_documents/repositories/permanent_document_repository.py`, `app/permanent_documents/repositories/permanent_document_query_repository.py`
- Services: `app/permanent_documents/services/permanent_document_service.py`, `app/permanent_documents/services/permanent_document_action_service.py`
- APIs: `app/permanent_documents/api/permanent_documents.py`, `app/permanent_documents/api/permanent_document_actions.py`

## API

Router prefix is `/api/v1/documents` (mounted in `app/main.py`).

### Upload document
- `POST /api/v1/documents/upload`
- Roles: `ADVISOR`, `SECRETARY`
- Multipart form fields:
  - `business_id` (required)
  - `document_type` (required)
  - `file` (required)
  - `tax_year` (optional)
  - `annual_report_id` (optional)
  - `notes` (optional)

### List business documents
- `GET /api/v1/documents/business/{business_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `tax_year` (optional)

### Get operational signals
- `GET /api/v1/documents/business/{business_id}/signals`
- Roles: `ADVISOR`, `SECRETARY`
- Returns missing document types advisory payload.

### Get download URL
- `GET /api/v1/documents/{document_id}/download-url`
- Roles: `ADVISOR`, `SECRETARY`
- Returns a presigned URL payload:

```json
{
  "url": "..."
}
```

### Delete document (soft delete)
- `DELETE /api/v1/documents/{document_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

### Replace document file
- `PUT /api/v1/documents/{document_id}/replace`
- Role: `ADVISOR` only
- Multipart form with `file`

### Approve document
- `POST /api/v1/documents/{document_id}/approve`
- Role: `ADVISOR` only

### Reject document
- `POST /api/v1/documents/{document_id}/reject`
- Role: `ADVISOR` only
- Body:

```json
{
  "notes": "reason"
}
```

### Update document notes
- `PATCH /api/v1/documents/{document_id}/notes`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "notes": "updated notes"
}
```

### Get document versions
- `GET /api/v1/documents/business/{business_id}/versions`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `document_type` (required)
  - `tax_year` (optional)

### List documents by annual report
- `GET /api/v1/documents/annual-report/{report_id}`
- Roles: `ADVISOR`, `SECRETARY`

## Behavior Notes

- Upload validates business existence (`PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND` on missing business).
- `scope` is derived automatically from `document_type`:
  - `id_copy`, `power_of_attorney`, `engagement_agreement` → `scope=CLIENT`, `business_id=NULL`
  - all other types → `scope=BUSINESS`, `business_id` required
- Upload is versioned per `(business_id, document_type, tax_year)`:
  - New upload increments version.
  - Previous latest document is linked via `superseded_by`.
  - The DB record is flushed first; storage upload happens second. On storage failure the transaction is rolled back (`DOCUMENT.UPLOAD_FAILED`).
  - `superseded_by` is set in the same commit as the new record — no inconsistency window.
  - Concurrent uploads of the same version are rejected with `DOCUMENT.VERSION_CONFLICT` (409).
- Storage key pattern: `businesses/{business_id}/{document_type}/{tax_year_or_permanent}/v{version}_{filename}`
- Allowed file types: PDF, Word, Excel, JPEG, PNG. Max size: 10 MB. Violations raise `DOCUMENT.INVALID_FILE_TYPE` / `DOCUMENT.FILE_TOO_LARGE` (422).
- Default missing-required types checked by signals:
  - `id_copy`
  - `power_of_attorney`
  - `engagement_agreement`
- `missing_by_type` checks both `business_id` (BUSINESS-scoped) and `client_id` (CLIENT-scoped) so that identity documents uploaded under the client are not falsely flagged as missing.
- List endpoints exclude soft-deleted documents.
- Delete marks `is_deleted=true` (soft delete); storage file is not removed.
- Replace updates the storage key, increments version, and updates all file metadata fields in a single commit.
- Approve records `approved_by` + `approved_at`. Reject records `rejected_by` + `rejected_at` + `notes`.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain error codes:
- `PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND` — business not found on upload
- `PERMANENT_DOCUMENTS.NOT_FOUND` — document not found or soft-deleted
- `DOCUMENT.FILE_TOO_LARGE` — file exceeds 10 MB limit
- `DOCUMENT.INVALID_FILE_TYPE` — MIME type not in allowed list
- `DOCUMENT.UPLOAD_FAILED` — storage upload failure
- `DOCUMENT.VERSION_CONFLICT` — concurrent upload collision (409)

## Cross-Domain Integration

- `infrastructure` integration:
  - Uses `StorageProvider` from `app/infrastructure/storage.py` for upload and presigned download URL generation.
- `businesses` integration:
  - Upload and signals are business-scoped; `business_id` is resolved to `client_id` at upload time.
- `clients` integration:
  - `client_id` is denormalized on every document for fast queries without a JOIN.
- `annual_reports` integration:
  - Documents can be linked to `annual_report_id` and queried per report.
- `binders/signals` integration:
  - Operational missing-document signals delegate to `SignalsService.compute_business_operational_signals`.

## Tests

Permanent-documents test suites:
- `tests/permanent_documents/api/test_permanent_documents.py`
- `tests/permanent_documents/api/test_api_authorization.py`
- `tests/permanent_documents/service/test_permanent_document.py`
- `tests/permanent_documents/service/test_permanent_document_list_delete.py`
- `tests/permanent_documents/repository/test_permanent_document_repository.py`

Run only this domain:

```bash
pytest tests/permanent_documents -q
```