# Invoice Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages external invoice references attached to charges (provider metadata, external invoice id, issue timestamp, and optional document URL).

## Scope

This module provides:
- Persistence of external invoice references in `invoices`
- One-to-one link between charge and invoice reference (`charge_id` unique)
- Service-level business rules for attaching invoice references to charges
- Repository getters for charge-based and id-based invoice lookup

## Domain Model

`Invoice` fields:
- `id` (PK)
- `charge_id` (FK -> `charges.id`, required, unique)
- `provider` (required)
- `external_invoice_id` (required)
- `document_url` (optional)
- `issued_at` (required)
- `created_at`

Implementation references:
- Model: `app/invoice/models/invoice.py`
- Schemas: `app/invoice/schemas/invoice_schemas.py`
- Repository: `app/invoice/repositories/invoice_repository.py`
- Service: `app/invoice/services/invoice_service.py`

## API

There is currently no standalone invoice HTTP router under `app/invoice/api`.

Invoice operations are currently exposed as internal service/repository logic and are intended to be integrated from billing/external provider flows (see TODO in `InvoiceService.attach_invoice_to_charge`).

## Behavior Notes

- `attach_invoice_to_charge` enforces these rules:
  - Charge must exist (`INVOICE.NOT_FOUND` if missing).
  - Charge must be in `issued` status (`INVOICE.INVALID_STATUS` otherwise).
  - A charge can have only one invoice reference (`INVOICE.CONFLICT` if already exists).
- Invoice metadata is treated as immutable after creation (no update method in service/repository).
- Repository supports:
  - `create`
  - `get_by_id`
  - `get_by_charge_id`
  - `list_by_charge_ids`
  - `exists_for_charge`
- `charge_id` uniqueness is enforced at both service and DB-model level.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `INVOICE.NOT_FOUND`
- `INVOICE.INVALID_STATUS`
- `INVOICE.CONFLICT`

## Cross-Domain Integration

- `charge` integration:
  - Invoice attachment depends on charge lifecycle status (`issued` only).
  - `InvoiceService` uses `ChargeRepository` to validate charge existence and status.
- Planned integration point:
  - `BillingService.issue_charge` is marked with TODO to call invoice attachment once external invoice provider integration is ready.
- Note:
  - VAT reports use a separate invoice model (`app/vat_reports/models/vat_invoice.py`) and are not backed by `app/invoice/models/invoice.py`.

## Tests

Invoice test suites:
- `tests/invoice/service/test_invoice_service_rules.py`
- `tests/invoice/repository/test_invoice_repository.py`

Related (separate VAT invoice domain) tests:
- `tests/vat_reports/repository/test_vat_invoice_repository.py`
- `tests/vat_reports/api/test_vat_reports_invoices.py`
- `tests/vat_reports/service/test_vat_report_invoices.py`

Run only this domain:

```bash
pytest tests/invoice -q
```
