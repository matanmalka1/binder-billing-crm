# Timeline Module

Provides unified per-client timeline aggregation across operational domains (binders, charges, notifications, tax deadlines, annual reports, reminders, documents, and signature requests).

## Scope

This module provides:
- Unified client timeline endpoint
- Event normalization into a shared timeline event schema
- Reverse-chronological ordering and pagination
- Backward-compatible action fields (`actions` + `available_actions`)
- Cross-domain event aggregation via dedicated builder modules

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
- Repository: `app/timeline/repositories/timeline_repository.py`
- Services:
  - `app/timeline/services/timeline_service.py`
  - `app/timeline/services/timeline_event_builders.py`
  - `app/timeline/services/timeline_tax_builders.py`
  - `app/timeline/services/timeline_client_aggregator.py`
  - `app/timeline/services/timeline_client_builders.py`

## API

Router prefix is `/api/v1/clients` (mounted in `app/main.py`).

### Get client timeline
- `GET /api/v1/clients/{client_id}/timeline`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `50`, min `1`, max `200`)

Response:
- `client_id`
- `events` (list of normalized timeline events)
- `page`
- `page_size`
- `total`

## Behavior Notes

- Timeline is aggregated from multiple domain sources, then sorted by `timestamp` descending.
- Pagination is applied after full event aggregation/sort.
- Event schema includes:
  - `event_type`
  - `timestamp`
  - optional `binder_id`, `charge_id`
  - `description`
  - `metadata`
  - optional `actions` and `available_actions`
- Action compatibility:
  - `available_actions` is kept for older clients.
  - `actions` and `available_actions` intentionally carry the same list for compatible event types.
- Known per-client bulk safety limit:
  - `_TIMELINE_BULK_LIMIT = 500`
  - Applied to high-volume sources (notifications, charges, reminders, signature requests, tax/annual queries).
  - Older events beyond cap can be truncated.

Main event categories currently built:
- Binder events:
  - `binder_received`, `binder_returned`, `binder_status_change`
- Financial/notification events:
  - `charge_created`, `charge_issued`, `charge_paid`, `invoice_attached`, `notification_sent`
- Tax/annual events:
  - `tax_deadline_due`, `annual_report_status_changed`
- Client context events:
  - `client_created`, `client_info_updated`, `tax_profile_updated`, `reminder_created`, `document_uploaded`, `signature_request_created`

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Authorization failures are handled by shared role/auth dependencies.

## Cross-Domain Integration

Timeline composes data from:
- `binders` + `binder_status_logs`
- `charge` + `invoice`
- `notification`
- `tax_deadline`
- `annual_reports`
- `reminders`
- `permanent_documents`
- `signature_requests`
- `clients` + `client_tax_profile`

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
