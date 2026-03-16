# Search Module

Provides unified search across clients, binders, and matching permanent documents, with optional operational filters (work state/signals).

## Scope

This module provides:
- Unified `/search` endpoint for clients and binders
- Optional document search results (filename/type) when `query` is provided
- Client-level DB search/pagination for simple client queries
- Mixed in-memory search mode for binder-derived filters
- Role-based API access

## Domain Model

This module does not define persistent database models.

It defines search response schemas and service logic:
- `SearchResult` (client/binder result)
- `DocumentSearchResult` (permanent document result)
- `SearchResponse`
- `SearchService`
- `DocumentSearchService`

Implementation references:
- API: `app/search/api/search.py`
- Schemas: `app/search/schemas/search.py`
- Services: `app/search/services/search_service.py`, `app/search/services/document_search_service.py`, `app/search/services/search_filters.py`

## API

Router prefix is `/api/v1/search` (mounted in `app/main.py`).

### Unified search
- `GET /api/v1/search`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `query` (optional)
  - `client_name` (optional)
  - `id_number` (optional)
  - `binder_number` (optional)
  - `work_state` (optional)
  - `signal_type` (optional list query param; repeatable)
  - `has_signals` (optional boolean)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

Response shape:
- `results`: list of client/binder search hits
- `documents`: list of document hits (when `query` is present)
- `page`, `page_size`, `total`

## Behavior Notes

- Result types:
  - `client` result includes client identity fields.
  - `binder` result includes `binder_id`, `binder_number`, derived `work_state`, and `signals`.
- Document search:
  - Triggered only when `query` is provided.
  - Searches permanent documents by filename/type.
  - Max document matches: `50`.
- Search execution modes:
  - Client-only DB mode (faster): when querying clients without binder-derived filters.
  - Mixed mode (in-memory post-processing): when binder filters/derived fields are involved.
- Mixed-mode safety ceilings:
  - `_MIXED_SEARCH_BINDER_LIMIT = 1000`
  - `_MIXED_SEARCH_CLIENT_LIMIT = 500`
  - Results beyond ceilings are excluded (known limitation).
- `signal_type` matching uses OR semantics (`any` requested signal present).

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Authorization failures are handled by shared role/auth dependencies.

## Cross-Domain Integration

Search composes data from:
- `clients` repository search (`client_name`, `id_number`, free query)
- `binders` repository + derived work-state/signals
- `permanent_documents` repository for document matches
- `binders` services:
  - `WorkStateService`
  - `SignalsService`

## Tests

Search test suites:
- `tests/search/api/test_search.py`
- `tests/search/api/test_search_db_filtering.py`

Run only this domain:

```bash
pytest tests/search -q
```
