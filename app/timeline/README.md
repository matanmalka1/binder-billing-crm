# Timeline Module

> Last audited: 2026-03-22 (domain-by-domain backend sync).

Provides unified per-business timeline aggregation across operational domains (binders, charges, notifications, tax deadlines, annual reports, reminders, documents, and signature requests).

## Scope

This module provides:
- Unified business timeline endpoint
- Event normalization into a shared timeline event schema
- Reverse-chronological ordering and pagination
- Backward-compatible action fields (`actions` + `available_actions`)
- Cross-domain event aggregation via dedicated builder modules
- Business existence validation on timeline fetch (raises `TIMELINE.BUSINESS_NOT_FOUND` if missing)

## Domain Model

This module does not define persistent database models.

It defines timeline response schemas and aggregation logic:
- `TimelineEvent`
- `ClientTimelineResponse`
- `TimelineService`
- Builder modules for binder/charge/notification/tax/client events

Implementation references:
- API: `app/timeline/api/timeline.py`
- Schemas: `app/timeline/schemas/timeline.py`
- Services:
  - `app/timeline/services/timeline_service.py`
  - `app/timeline/services/timeline_binder_event_builders.py`
  - `app/timeline/services/timeline_charge_event_builders.py`
  - `app/timeline/services/timeline_tax_builders.py`
  - `app/timeline/services/timeline_client_aggregator.py`
  - `app/timeline/services/timeline_client_builders.py`
  - `app/timeline/services` is the orchestration layer; it queries source domains directly (no dedicated `timeline/repositories` package currently exists)

Note: `timeline_event_builders.py` has been split into `timeline_binder_event_builders.py` and `timeline_charge_event_builders.py` for maintainability.

## API

Router prefix is `/api/v1/businesses` (mounted in `app/main.py`).

### Get business timeline
- `GET /api/v1/businesses/{business_id}/timeline`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `200`)

Response:
- `business_id`
- `events` (list of normalized timeline events)
- `page`
- `page_size`
- `total`

## Behavior Notes

- Timeline is aggregated from multiple domain sources, then sorted by `timestamp` descending.
- Pagination is applied after full event aggregation/sort.
- Business existence is validated at the start of every timeline fetch; missing or deleted businesses raise `NotFoundError` (`TIMELINE.BUSINESS_NOT_FOUND`).
- Binders are fetched via `business.client_id` (binders belong to clients, not businesses directly).
- Event schema includes:
  - `event_type`
  - `timestamp`
  - optional `binder_id`, `charge_id`
  - `description`
  - `metadata`
  - optional `actions` and `available_actions`
- Action compatibility:
  - `available_actions` is the canonical field for frontend executors.
  - `actions` is kept for backward compatibility; both fields carry the same list.
- Known per-business bulk safety limit:
  - `_TIMELINE_BULK_LIMIT = 500`
  - Applied to high-volume sources (notifications, charges, reminders, signature requests, documents, tax/annual queries).
  - Older events beyond the cap are silently truncated.
- `client_info_updated_event` is only emitted when `business.updated_at` differs from `business.created_at` (avoids duplicate creation-time events).
- Tax deadlines query filters soft-deleted rows (`deleted_at IS NULL`).
- Annual reports query filters soft-deleted rows (`deleted_at IS NULL`).

Main event categories currently built:
- Binder events:
  - `binder_received`, `binder_returned`, `binder_status_change`
- Notification events:
  - `notification_sent`
- Financial events:
  - `charge_created`, `charge_issued`, `charge_paid`, `invoice_attached`
- Tax/annual events:
  - `tax_deadline_due`, `annual_report_status_changed`
- Client/business context events:
  - `client_created`, `client_info_updated`, `tax_profile_updated`, `reminder_created`, `document_uploaded`, `signature_request_created`

### Hebrew label maps

`timeline_binder_event_builders.py` maps binder statuses and notification triggers to Hebrew labels. `timeline_client_builders.py` covers all reminder types including newer entries (`vat_filing`, `advance_payment_due`, `annual_report_deadline`, `document_missing`). `timeline_charge_event_builders.py` maps the full `ChargeType` enum to Hebrew.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain error codes:
- `TIMELINE.BUSINESS_NOT_FOUND` — business does not exist or is soft-deleted

Authorization failures are handled by shared role/auth dependencies.

## Cross-Domain Integration

Timeline composes data from:
- `businesses` (existence check; `client_id` resolution for binder queries)
- `binders` + `binder_status_logs`
- `charge` + `invoice`
- `notification`
- `tax_deadline` (soft-delete filtered)
- `annual_reports` (soft-delete filtered)
- `reminders`
- `permanent_documents`
- `signature_requests`
- `businesses` + `business_tax_profile` (for client context events)

## Tests

Timeline test suites:
- `tests/timeline/api/test_timeline.py`
- `tests/timeline/service/test_timeline_service_get_client_timeline.py`
- `tests/timeline/service/test_timeline_event_builders.py`
- `tests/timeline/service/test_timeline_event_builders_additional.py`
- `tests/timeline/service/test_timeline_tax_builders.py`
- `tests/timeline/service/test_timeline_client_aggregator.py`
- `tests/timeline/service/test_timeline_client_builders.py`
- `tests/timeline/repository/test_timeline_repository.py`

Run only this domain:

```bash
pytest tests/timeline -q
```
