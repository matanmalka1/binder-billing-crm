# Permanent Documents Module

> Last audited: 2026-03-22 (post-refactor sync).

Manages client permanent documents (upload, versioning, status actions, retrieval, and advisory missing-doc signals) used across operational and annual-report workflows.

## Scope

This module provides:
- Permanent-document upload and retrieval
- Client document listing with optional tax-year filtering
- Document replacement and soft delete
- Document workflow actions (update notes, version history, annual-report listing)
- Version history queries by document type/year
- Annual-report scoped document listing
- Operational missing-document signals per client record
- Role-based API access

## Domain Model

`PermanentDocument` fields:
- `id` (PK)
- `client_record_id` (FK -> `client_records.id`, required — denormalized for fast queries)
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
- `client` — client-record documents. `business_id` is NULL.
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

Router prefix is `/api/v1/documents` (mounted via `app/router_registry.py`).

### Upload document
- `POST /api/v1/documents/upload`
- Roles: `ADVISOR`, `SECRETARY`
- Multipart form fields:
  - `client_record_id` (required)
  - `document_type` (required)
  - `file` (required)
  - `business_id` (optional; when present the document is business-scoped)
  - `tax_year` (optional)
  - `annual_report_id` (optional)
  - `notes` (optional)

### List client documents
- `GET /api/v1/documents/client/{client_record_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `tax_year` (optional)

### Get operational signals
- `GET /api/v1/documents/client/{client_record_id}/signals`
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
- `GET /api/v1/documents/client/{client_record_id}/versions`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `document_type` (required)
  - `tax_year` (optional)

### List documents by annual report
- `GET /api/v1/documents/annual-report/{report_id}`
- Roles: `ADVISOR`, `SECRETARY`

## Behavior Notes

- Upload validates client-record existence and, when `business_id` is provided, business ownership under the same legal entity.
- `scope` is derived from whether `business_id` is provided:
  - no `business_id` → `scope=CLIENT`
  - with `business_id` → `scope=BUSINESS`
- Upload is versioned per `(client_record_id, business_id, document_type, tax_year)`:
  - New upload increments version.
  - Previous latest document is linked via `superseded_by`.
  - The DB record is flushed first; storage upload happens second. On storage failure the transaction is rolled back (`DOCUMENT.UPLOAD_FAILED`).
  - `superseded_by` is set in the same commit as the new record — no inconsistency window.
  - Concurrent uploads of the same version are rejected with `DOCUMENT.VERSION_CONFLICT` (409).
- Storage key pattern:
  - business-scoped: `businesses/{business_id}/{document_type}/{tax_year_or_permanent}/v{version}_{filename}`
  - client-scoped: `clients/{client_record_id}/{document_type}/{tax_year_or_permanent}/v{version}_{filename}`
- Allowed file types: PDF, Word, Excel, JPEG, PNG. Max size: 10 MB. Violations raise `DOCUMENT.INVALID_FILE_TYPE` / `DOCUMENT.FILE_TOO_LARGE` (422).
- Default missing-required types checked by signals:
  - `id_copy`
  - `power_of_attorney`
  - `engagement_agreement`
- Client-level missing-document signals check latest non-deleted client-record documents.
- List endpoints exclude soft-deleted documents.
- Delete marks `is_deleted=true` (soft delete); storage file is not removed.
- Replace updates the storage key, increments version, and updates all file metadata fields in a single commit.
- Upload currently stores new documents as approved and records `approved_by` + `approved_at`; there are no standalone approve/reject HTTP endpoints.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain error codes:
- `CLIENT_RECORD.NOT_FOUND` — client record not found on upload/list
- `PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND` — business not found on business-scoped upload
- `PERMANENT_DOCUMENTS.NOT_FOUND` — document not found or soft-deleted
- `DOCUMENT.FILE_TOO_LARGE` — file exceeds 10 MB limit
- `DOCUMENT.INVALID_FILE_TYPE` — MIME type not in allowed list
- `DOCUMENT.UPLOAD_FAILED` — storage upload failure
- `DOCUMENT.VERSION_CONFLICT` — concurrent upload collision (409)

## Cross-Domain Integration

- `infrastructure` integration:
  - Uses `StorageProvider` from `app/infrastructure/storage.py` for upload and presigned download URL generation.
- `businesses` integration:
  - Business-scoped uploads validate `business_id` against the client record's legal entity.
- `clients` integration:
  - `client_record_id` is denormalized on every document for fast queries without a JOIN.
- `annual_reports` integration:
  - Documents can be linked to `annual_report_id` and queried per report.
- `binders/signals` integration:
  - Business-level signal helpers can delegate to `SignalsService.compute_business_operational_signals`.

## Tests

Permanent-documents test suites:
- `tests/permanent_documents/api/test_permanent_documents.py`
- `tests/permanent_documents/api/test_api_authorization.py`
- `tests/permanent_documents/api/test_permanent_document_actions.py`
- `tests/permanent_documents/service/test_permanent_document.py`
- `tests/permanent_documents/service/test_permanent_document_service_additional.py`
- `tests/permanent_documents/service/test_permanent_document_action_service.py`
- `tests/permanent_documents/service/test_permanent_document_list_delete.py`
- `tests/permanent_documents/repository/test_permanent_document_repository.py`

Run only this domain:

```bash
pytest tests/permanent_documents -q
```
