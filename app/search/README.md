# Search Module

> Last audited: 2026-03-22.

Unified search endpoint for clients, active binders, and matching permanent documents.

## Scope

This module provides:
- Unified `GET /api/v1/search` endpoint
- Optional document matches when `query` is provided
- Fast DB-paginated client-only mode
- Mixed in-memory mode when binder-derived filters are requested
- Role-gated access (`ADVISOR`, `SECRETARY`)

This module does not define DB models. It is an orchestration layer over existing repositories/services.

## Files

- API: `app/search/api/search.py`
- Schemas: `app/search/schemas/search.py`
- Services:
  - `app/search/services/search_service.py`
  - `app/search/services/document_search_service.py`
  - `app/search/services/search_filters.py`

## Routing

- Router prefix inside module: `/search`
- App mount: `app/router_registry.py` adds this router with prefix `/api/v1`
- Effective endpoint: `GET /api/v1/search`

## Query Parameters

- `query` (optional)
- `client_name` (optional)
- `id_number` (optional)
- `binder_number` (optional)
- `signal_type` (optional, repeatable list param)
- `has_signals` (optional bool)
- `page` (default `1`, min `1`)
- `page_size` (default `20`, min `1`, max `100`)

## Response Shape

`SearchResponse`:
- `results: SearchResult[]`
- `documents: DocumentSearchResult[]`
- `page: int`
- `page_size: int`
- `total: int` (count of `results`, not `documents`)

`SearchResult` (`result_type: "client" | "binder"`):
- `client_id`, `client_name`
- `binder_id`, `binder_number` (binder rows only)
- `signals` (binder rows only)
- `client_status` is currently always `null`

`DocumentSearchResult`:
- `id`, `business_id`, `client_name`, `document_type`, `original_filename`, `tax_year`, `status`
- Note: `client_name` here is populated from `Business.full_name` (naming legacy in schema)

## Execution Modes

### 1) Client-only DB mode (fast path)
Triggered when:
- at least one of `query`, `client_name`, `id_number` is present
- and none of `signal_type`, `has_signals`, `binder_number` is provided

Behavior:
- Uses `ClientRepository.search(...)` with DB pagination (`page`, `page_size`)
- Returns only `client`-type rows in `results`

### 2) Mixed mode (in-memory post-filter + pagination)
Triggered for binder-related filtering/search.

Behavior:
- Builds a combined result list in memory, then paginates in memory
- Client side of mixed mode fetches up to `_MIXED_SEARCH_CLIENT_LIMIT = 500`
- Binder side fetches active binders up to `_MIXED_SEARCH_BINDER_LIMIT = 1000`
- Anything beyond those ceilings is excluded from results

Binder matching details:
- Base binder source is `BinderRepository.list_active(...)` (non-returned + non-deleted)
- If `binder_number` is provided, it is used as DB binder-number filter
- Else, if `query` is provided and `client_name`/`id_number` are not provided, `query` is reused as binder-number filter
- Derived fields per binder:
  - `signals` via `SignalsService.compute_binder_signals(...)`
- `signal_type` uses OR semantics (`any` requested signal is enough)
- `has_signals=true` means `len(signals) > 0`; `false` means no signals

## Document Search

Executed only when `query` is provided.

- Service: `DocumentSearchService.search_documents(query)`
- Repository call: `PermanentDocumentRepository.search_by_query(query, limit=50)`
- Search fields: `original_filename` OR `document_type` (ILIKE)
- Includes only non-deleted and non-superseded permanent documents
- Enriches each result with business name using `BusinessRepository.get_by_id(...)` (with in-call cache)

## Data Constraints

- Clients: only active/non-deleted clients (`Client.deleted_at IS NULL`)
- Binders: only active binders (`status != RETURNED` and `deleted_at IS NULL`)
- Permanent documents: non-deleted and latest version (`superseded_by IS NULL`)

## Known Limitations

- Mixed mode has hard safety ceilings (`500` clients, `1000` binders)
- In mixed mode, ordering is construction order (clients first, then binders), not a global relevance score
- A client can appear both as a `client` row and as one or more `binder` rows

## Error/Authorization

- Authorization is enforced by shared role dependency (`require_role`)
- Error envelope follows global app error format from `app/core/exceptions.py`

## Tests

- API:
  - `tests/search/api/test_search.py`
  - `tests/search/api/test_search_db_filtering.py`
- Service:
  - `tests/search/service/test_search_service.py`
  - `tests/search/service/test_document_search_service.py`
  - `tests/search/service/test_search_filters.py`

Run:

```bash
pytest tests/search -q
```
