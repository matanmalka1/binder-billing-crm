# Timeline Module

> Last audited: 2026-05-08 (operational feed cleanup).

Provides a per-client-record operational activity feed. The timeline shows
meaningful business milestones only; generic audit/history rows and automated
notification/reminder noise are intentionally excluded.

## Scope

This module provides:
- Unified client timeline endpoint
- Event normalization into a shared timeline event schema
- Reverse-chronological ordering and pagination
- Cross-domain event aggregation via dedicated builder modules
- Client-record existence validation on timeline fetch (raises `TIMELINE.CLIENT_NOT_FOUND` if missing)

## Domain Model

This module does not define persistent database models.

It defines timeline response schemas and aggregation logic:
- `TimelineEvent`
- `ClientTimelineResponse`
- `TimelineService`
- Builder modules for binder, charge, tax, document, and signature events

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

Router prefix is `/api/v1/clients` (mounted via `app/router_registry.py`).

### Get client timeline
- `GET /api/v1/clients/{client_record_id}/timeline`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `200`)

Response:
- `client_record_id`
- `events` (list of normalized timeline events)
- `page`
- `page_size`
- `total`

## Behavior Notes

- Timeline is aggregated from multiple domain sources, then sorted by `timestamp` descending.
- Pagination is applied after full event aggregation/sort.
- Client-record existence is validated at the start of every timeline fetch; missing records raise `NotFoundError` (`TIMELINE.CLIENT_NOT_FOUND`).
- Businesses are resolved from the client record's `legal_entity_id`; business-scoped sources are queried across those businesses.
- Event schema includes:
  - `event_type`
  - `timestamp`
  - optional `binder_id`, `charge_id`
  - `description`
  - `metadata`
- Timeline events are informational only and do not include executable action fields.
- Known per-client bulk safety limit:
  - `_TIMELINE_BULK_LIMIT = 500`
  - Applied to high-volume sources (charges, documents, signatures, annual queries).
  - Older events beyond the cap are silently truncated.
- Annual report events are emitted from `annual_report_status_history`, not
  from the current report row.
- Signature lifecycle events are emitted from `signature_audit_events`.

Main event categories currently built:
- Binder events:
  - `binder_received`, `binder_handed_over`, `binder_lifecycle_change`
- Financial events:
  - `charge_created`, `charge_issued`, `charge_paid`, `invoice_attached`
- Tax/annual events:
  - `annual_report_status_changed`
- Client/business context events:
  - `client_created`, `document_uploaded`
- Signature events:
  - `signature_request_sent`
  - `signature_request_signed`
  - `signature_request_declined`
  - `signature_request_canceled`
  - `signature_request_expired`

Explicitly excluded noisy events:
- `client_info_updated` — belongs in generic audit.
- `reminder_created` — raw reminder setup is not client activity.
- `notification_sent` — automated send rows are noisy.
- `signature_request_created` — lifecycle audit rows are more useful.
- Initial binder `null -> in_office` lifecycle logs when `binder_received` exists.
- Same-value binder lifecycle log rows.

Not included in this module currently:
- Tax calendar upcoming deadlines.
- VAT report lifecycle events.
- Advance payment lifecycle events.
- Correspondence entries.

### Hebrew label maps

`timeline_binder_event_builders.py` maps binder lifecycle values to Hebrew labels.
`timeline_charge_event_builders.py` maps the full `ChargeType` enum to Hebrew.
`timeline_tax_builders.py` maps annual report status transitions.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `error.code`
- `error.message`
- `error.details` (null or domain-specific object)
- `error.request_id` (when available)

Domain error codes:
- `TIMELINE.CLIENT_NOT_FOUND` — client record does not exist

Authorization failures are handled by shared role/auth dependencies.

## Cross-Domain Integration

Timeline composes data from:
- `clients` (client-record existence check; `legal_entity_id` resolution)
- `businesses` (business IDs for business-scoped event sources)
- `binders` + `binder_lifecycle_logs`
- `charge` + `invoice`
- `annual_reports` + `annual_report_status_history`
- `permanent_documents`
- `signature_requests` + `signature_audit_events`

## Tests

Timeline test suites:
- `tests/timeline/api/test_timeline.py`
- `tests/timeline/service/test_timeline_service_get_client_timeline.py`
- `tests/timeline/service/test_timeline_event_builders.py`
- `tests/timeline/service/test_timeline_event_builders_additional.py`
- `tests/timeline/service/test_timeline_tax_builders.py`
- `tests/timeline/service/test_timeline_client_builders.py`
- `tests/timeline/service/test_timeline_operational_policy.py`
- `tests/timeline/service/test_timeline_signature_lifecycle.py`
- `tests/timeline/repository/test_timeline_repository.py`

Run only this domain:

```bash
pytest tests/timeline -q
```
