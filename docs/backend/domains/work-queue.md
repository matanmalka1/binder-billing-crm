## Scope
This file owns only:
- Implemented Work Queue construction, scoping, urgency, and response-shape behavior.
- Current Work Queue source types and aggregation rules.

This file must not contain:
- Product rules for the source domains that feed the queue.
- Frontend UI behavior.
- Cross-project architecture rules.

Source of truth: mandatory

# Work Queue Domain

## What It Is

The work queue is a unified, computed view of everything that needs attention in the system. It aggregates items from multiple source domains into a single prioritized list. Items are never stored in a `work_queue` table — the entire list is built in-memory on every request.

## Source Types

```python
class WorkQueueSourceType(str, PyEnum):
    VAT_WORK_ITEM = "vat_work_item"
    ANNUAL_REPORT = "annual_report"
    ADVANCE_PAYMENT = "advance_payment"
    CHARGE = "charge"
    BINDER = "binder"
    TASK = "task"
```

System items (derived from domain state): `VAT_WORK_ITEM`, `ANNUAL_REPORT`, `ADVANCE_PAYMENT`, `CHARGE`, `BINDER`.

Manual items: `TASK` (user-created tasks from `app/tasks/`).

## Entry Point

```
GET /api/v1/work-queue
  → WorkQueueService.list_items_with_total(...)
  → returns WorkQueueListResponse { items, total, summary }
```

## How Items Are Built

`WorkQueueService._build_items()`:

1. Loads system items from each source domain's builder:
   - `vat_work_item_items(ctx, client_record_id)` — from `app/work_queue/services/tax_items.py`
   - `annual_report_items(ctx, client_record_id)`
   - `advance_payment_items(ctx, client_record_id)` — from `billing_items.py`
   - `charge_items(ctx, client_record_id, business_id)` — from `billing_items.py`
   - `binder_items(ctx)` — from `binder_items.py` — only when no client/business filter

2. Attaches UI actions to each system item via `source_actions(source_type, source_id)`.

3. Loads tasks via `TaskRepository.list_for_work_queue(include_history=include_task_history)`.

4. Merges tasks with system items (`_merge_tasks()`):
   - If a task is `OPEN` and linked to a known system item → task is attached as `linked_tasks` on the system item
   - Otherwise → task becomes a standalone `WorkQueueItem` with `source_type=TASK`

5. Applies filters (`apply_work_queue_filters()`).

6. Sorts by urgency → due_date → item kind (TASK first) → priority.

## Scoping Rules

| Filter | Effect |
|--------|--------|
| `client_record_id` | Narrows all source types to that client |
| `business_id` | Narrows charge items; VAT/annual reports/advance payments are skipped entirely (they are client-level, not business-level) |
| Neither | Returns all items across all active clients |

Binder items are only included when no `client_record_id` or `business_id` filter is active (they are not currently implemented as client-scoped in the query surface).

## Urgency

```python
APPROACHING_DAYS = 7
IMPORTANT_DAYS   = 21

def urgency(due_date: date, today: date) -> WorkQueueUrgency:
    days = (due_date - today).days
    if days < 0:   return OVERDUE
    if days <= 7:  return APPROACHING
    if days <= 21: return IMPORTANT
    return UPCOMING
```

Urgency from linked tasks can escalate a system item's urgency (but never downgrade it).

## WorkQueueContext

`WorkQueueContext` is a request-scoped helper passed to all item builders. It:
- Holds the `db` session and `today`
- Lazily resolves client display names/numbers in a single batch query when first needed
- Provides a factory method `ctx.item(...)` that constructs a `WorkQueueItem` and registers the client ID for deferred name resolution

This avoids N+1 queries when building a large list with client identity data.

## WorkQueueItem Schema

```python
class WorkQueueItem(BaseModel):
    id: str                                # "{source_type}:{source_id}"
    source_type: WorkQueueSourceType
    source_id: int
    title: str
    description: str | None
    type_label: str | None                 # Hebrew label for the source type
    status_label: str | None               # Hebrew label for current status
    due_date: date | None
    urgency: WorkQueueUrgency
    client_record_id: int | None
    client_name: str | None
    office_client_number: int | None
    business_id: int | None
    source_summary: WorkQueueSourceSummary | None
    linked_tasks: list[LinkedTaskSummary]
    linked_tasks_count: int
    warnings: list[WorkQueueWarning]
    available_actions: list[ActionDescriptor]
    metadata: dict | None                  # source-specific fields (period, priority, etc.)
```

`id` is a stable string key: `"vat_work_item:42"`, `"task:7"`. Used by the frontend for stable React keys.

## Warnings

Items can accumulate `WorkQueueWarning` entries for conditions like:
- `source_missing` — a task is linked to a source that no longer exists
- `source_final` — a task is linked to a source that is already in a terminal state
- `source_unknown` — a task's `source_domain` is not a recognized `WorkQueueSourceType`
- `multiple_linked_tasks` — a system item has more than one open task linked to it

## Filters

| Parameter | Type | Effect |
|-----------|------|--------|
| `client_record_id` | int | Scope to one client |
| `business_id` | int | Scope to one business |
| `exclude_source_types` | list[WorkQueueSourceType] | Omit source types |
| `search` | str | Case-insensitive fulltext across title, description, client, metadata fields |
| `source_type` | WorkQueueSourceType | Include only this source type |
| `urgency` | WorkQueueUrgency | Include only this urgency level |
| `task_status` | TaskStatus | Include items with matching task status |
| `linked` | LINKED \| UNLINKED | Filter by whether tasks are linked |
| `scope` | SYSTEM \| MANUAL | SYSTEM = non-TASK items; MANUAL = TASK items only |
| `include_task_history` | bool | Include historical DONE/CANCELED standalone task rows instead of active standalone task rows; system items are still returned |
| `limit` | int (1-200) | Page size, default 50 |
| `offset` | int | Page offset |

## Summary

`WorkQueueSummary` reflects the **full filtered set** before pagination applies:

```python
class WorkQueueSummary(BaseModel):
    total: int
    manual_tasks: int
    linked: int
    unlinked: int
    overdue: int
    approaching: int
    important: int
    upcoming: int
    by_source_type: dict[WorkQueueSourceType, int]
    by_task_status: dict[str, int]
```

## No Persistence

There is no `work_queue` table. Items have no database ID. The `id` field (`"vat_work_item:42"`) is assembled from the source type and source entity's PK.

This means:
- Filtering by computed fields (urgency, warnings) is done in Python after loading all source items
- There is a hard limit on the total items (`limit` max 200) to keep response times acceptable
- Very large offices with thousands of items may see slower responses on unscoped requests
