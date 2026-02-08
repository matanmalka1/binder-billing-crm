# Sprint 2 Quick Reference

## New API Endpoints

### Operational Binder Queries (ADVISOR + SECRETARY)

```
GET /api/v1/binders/open?page=1&page_size=20
GET /api/v1/binders/overdue?page=1&page_size=20
GET /api/v1/binders/due-today?page=1&page_size=20
GET /api/v1/clients/{client_id}/binders?page=1&page_size=20
```

Response format:
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 123,
      "binder_number": "BND-2026-001",
      "status": "in_office",
      "received_at": "2026-01-01",
      "expected_return_at": "2026-04-01",
      "returned_at": null,
      "pickup_person_name": null,
      "is_overdue": true,
      "days_overdue": 38
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 45
}
```

### Dashboard Overview (ADVISOR ONLY)

```
GET /api/v1/dashboard/overview
```

Response format:
```json
{
  "total_clients": 150,
  "active_binders": 45,
  "overdue_binders": 12,
  "binders_due_today": 3,
  "binders_due_this_week": 18
}
```

### Binder History (ADVISOR + SECRETARY)

```
GET /api/v1/binders/{binder_id}/history
```

Response format:
```json
{
  "binder_id": 1,
  "history": [
    {
      "old_status": "null",
      "new_status": "in_office",
      "changed_by": 1,
      "changed_at": "2026-01-01T10:00:00",
      "notes": "Binder received"
    },
    {
      "old_status": "in_office",
      "new_status": "ready_for_pickup",
      "changed_by": 1,
      "changed_at": "2026-01-15T14:30:00",
      "notes": null
    }
  ]
}
```

## SLA Logic

### Definitions (Derived at Read Time)

**Open Binder:**
- status != RETURNED

**Overdue Binder:**
- expected_return_at < today AND
- status != RETURNED

**Due Today:**
- expected_return_at == today AND
- status != RETURNED

### Derived Fields

- `is_overdue`: boolean
- `days_overdue`: integer (>= 0, returns 0 if not overdue)

## Authorization

| Endpoint                  | ADVISOR | SECRETARY |
|---------------------------|---------|-----------|
| /binders/open             | ✅       | ✅         |
| /binders/overdue          | ✅       | ✅         |
| /binders/due-today        | ✅       | ✅         |
| /clients/{id}/binders     | ✅       | ✅         |
| /binders/{id}/history     | ✅       | ✅         |
| /dashboard/overview       | ✅       | ❌         |

## Error Codes

- 200: Success
- 403: Forbidden (insufficient permissions)
- 404: Not found (binder or client)

## Pagination

All list endpoints support:
- `page` (default: 1, min: 1)
- `page_size` (default: 20, min: 1, max: 100)

## Key Implementation Details

1. **No Status Mutation**: Sprint 2 reads do NOT mutate binder status to OVERDUE
2. **Centralized SLA**: All overdue logic in `SLAService`
3. **Query-Time Derivation**: SLA fields computed on-the-fly, not stored
4. **Consistent Ordering**: Deterministic ordering for reproducible pagination
5. **Repository Extensions**: Sprint 2 queries in separate file from existing code

## Testing Examples

### Test Overdue Logic
```bash
# Create binder with expected_return_at in the past
# Query /binders/overdue
# Verify is_overdue=true and days_overdue calculated correctly
```

### Test Authorization
```bash
# As SECRETARY user
# GET /dashboard/overview
# Expect 403 Forbidden
```

### Test Pagination
```bash
# GET /binders/open?page=1&page_size=5
# GET /binders/open?page=2&page_size=5
# Verify no duplicates across pages
```

## Architecture Notes

- **Layers**: Router → Service → Repository → Model
- **No ORM Leakage**: All responses use Pydantic schemas
- **Dependency Injection**: Role guards via FastAPI dependencies
- **File Size**: All files under 150 lines
- **Separation**: Sprint 2 code is additive, minimal changes to existing code