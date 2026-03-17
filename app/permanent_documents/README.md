# Permanent Documents Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages client permanent documents (upload, versioning, status actions, retrieval, and advisory missing-doc signals) used across operational and annual-report workflows.

## Scope

This module provides:
- Permanent-document upload and retrieval
- Client document listing with optional tax-year filtering
- Document replacement and soft delete
- Document workflow actions (approve/reject/update notes)
- Version history queries by document type/year
- Annual-report scoped document listing
- Operational missing-document signals per client
- Role-based API access

## Domain Model

`PermanentDocument` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `document_type` (required)
- `storage_key` (required)
- `tax_year` (optional)
- `is_present` (default `true`)
- `is_deleted` (default `false`)
- `uploaded_by` (FK -> `users.id`, required)
- `uploaded_at`
- `version` (default `1`)
- `superseded_by` (self-reference to newer version)
- `status` (default `pending`)
- `annual_report_id` (optional FK -> `annual_reports.id`)
- `original_filename`, `file_size_bytes`, `mime_type`, `notes` (optional metadata)
- `approved_by`, `approved_at`

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
  - `client_id` (required)
  - `document_type` (required)
  - `file` (required)
  - `tax_year` (optional)
  - `annual_report_id` (optional)
  - `notes` (optional)

### List client documents
- `GET /api/v1/documents/client/{client_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `tax_year` (optional)

### Get operational signals
- `GET /api/v1/documents/client/{client_id}/signals`
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
- `GET /api/v1/documents/client/{client_id}/versions`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `document_type` (required)
  - `tax_year` (optional)

### List documents by annual report
- `GET /api/v1/documents/annual-report/{report_id}`
- Roles: `ADVISOR`, `SECRETARY`

## Behavior Notes

- Upload validates client existence (`PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND` on missing client).
- Upload is versioned per `(client_id, document_type, tax_year)`:
  - New upload increments version.
  - Previous latest document is linked via `superseded_by`.
- Storage key pattern includes client/type/year/version.
- Default missing-required types are:
  - `id_copy`
  - `power_of_attorney`
  - `engagement_agreement`
- List endpoints exclude soft-deleted documents.
- Delete marks `is_deleted=true` (soft delete), does not remove storage or row.
- Replace updates storage key and increments version on existing record.
- Approve/reject/notes actions operate only on non-deleted documents.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND`
- `PERMANENT_DOCUMENTS.NOT_FOUND`

## Cross-Domain Integration

- `infrastructure` integration:
  - Uses `StorageProvider` from `app/infrastructure/storage.py` for upload and presigned download URL generation.
- `clients` integration:
  - All document records are client-scoped.
- `annual_reports` integration:
  - Documents can be linked to `annual_report_id` and queried per report.
- `binders/signals` integration:
  - Operational missing-document signals are exposed via client signals endpoint.

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
