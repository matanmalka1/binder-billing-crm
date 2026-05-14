# WU-19 | B-14 — Consolidate Domain + Work Queue Action Systems

## Context

Two parallel action-building systems exist. Domain detail endpoints (binders, charges, businesses, VAT, annual reports, timeline) produce `ActionContract` (TypedDict, nested confirm). Work queue produces `WorkQueueAction` (Pydantic, flat confirm). This sprint consolidates domain actions + work queue actions into a single `ActionDescriptor` schema.

**Explicit exception — dashboard quick actions**: `app/actions/obligation_orchestrator.py` and `app/dashboard/services/_quick_actions_helpers.py` implement the `DashboardQuickAction` contract — a distinct product concept that embeds action metadata alongside product context fields (`category`, `urgency`, `due_date`, `due_label`, `description`, `client_name`, `binder_number`). This is intentionally separate from `ActionDescriptor` and is excluded from this migration. `build_action`/`build_confirm` survive in `action_helpers.py` for dashboard use only.

## Field Mapping: ActionContract → ActionDescriptor

| ActionContract field | ActionDescriptor field | Notes |
|---|---|---|
| `key` | `key` | direct |
| `label` | `label` | direct |
| `method` | `method` | direct |
| `endpoint` | `endpoint` | direct |
| `id` | — | **dropped** — frontend uses `key` |
| `payload` (dict) | `payload_schema="simple"` | business actions — payload dropped; frontend uses own mutation, not executeAction |
| `confirm.title` | `confirm_title` | flat |
| `confirm.message` | `confirm_message` | flat |
| `confirm_label`, `cancel_label` | — | **dropped** (see UX note below) |
| `confirm.inputs[]` | `payload_schema="requires_input"` | binder `return` action only |
| _(absent)_ | `type="mutation"` | all domain actions are mutations |
| _(absent)_ | `variant="secondary"` default | `"danger"` for destructive |

**UX behavior change — confirm_label/cancel_label removal**: The binder, charge, and business actions currently carry custom confirm button labels (e.g., `"אשר ביטול"`, `"הקפאה"`). These are dropped. The frontend's `mapConfirm` will substitute defaults (`"אישור"` / `"ביטול"`). This is an intentional simplification — custom labels provided no distinct UX value in practice.

**Business action payload**: `freeze`/`activate` are in frontend `HIDDEN_ACTION_KEYS` — filtered before render. `close` goes through `mapActions` but `ClientBusinessesCard` uses its own `updateBusinessStatus` mutation and does not consume `available_actions` via `executeAction`. Safe to use `payload_schema="simple"` with no payload dict.

---

## Step-by-Step Plan

### Stage 1 — Backend Schema + Builders

#### Step 1 — Create `app/core/action_schemas.py`
Single source of truth for the action type. `payload_schema` is strictly typed.

```python
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel

class ActionDescriptor(BaseModel):
    key: str
    label: str
    type: Literal["link", "mutation", "modal"]
    route: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[Literal["get", "post", "patch", "put", "delete"]] = None
    task_id: Optional[int] = None
    payload_schema: Literal["none", "simple", "requires_input"] = "none"
    confirm: bool = False
    confirm_title: Optional[str] = None
    confirm_message: Optional[str] = None
    variant: Literal["primary", "secondary", "danger"] = "secondary"
    disabled: bool = False
    disabled_reason: Optional[str] = None

__all__ = ["ActionDescriptor"]
```

#### Step 2 — Create `app/core/action_builders.py`
Public builder functions — named without underscore (they are cross-domain public API). Invariants enforced via required parameters.

```python
from __future__ import annotations
from typing import Literal, Optional
from app.core.action_schemas import ActionDescriptor

ActionVariant = Literal["primary", "secondary", "danger"]

def link_action(key: str, label: str, route: str, *, primary: bool = False) -> ActionDescriptor:
    # route is required — link_action without route is invalid
    return ActionDescriptor(key=key, label=label, type="link", route=route,
                            variant="primary" if primary else "secondary")

def mutation_action(
    key: str, label: str, endpoint: str, *,
    method: Literal["get","post","patch","put","delete"] = "post",
    task_id: Optional[int] = None,
    confirm_title: Optional[str] = None,
    confirm_message: Optional[str] = None,
    variant: ActionVariant = "secondary",
    payload_schema: Literal["none","simple","requires_input"] = "none",
) -> ActionDescriptor:
    # endpoint is required — mutation without endpoint is invalid
    return ActionDescriptor(
        key=key, label=label, type="mutation", endpoint=endpoint, method=method,
        task_id=task_id,
        confirm=confirm_title is not None or confirm_message is not None,
        confirm_title=confirm_title, confirm_message=confirm_message,
        variant=variant, payload_schema=payload_schema,
    )

def modal_action(
    key: str, label: str, *,
    task_id: Optional[int] = None,
    primary: bool = False,
    variant: Optional[ActionVariant] = None,
) -> ActionDescriptor:
    return ActionDescriptor(key=key, label=label, type="modal", task_id=task_id,
                            variant=variant or ("primary" if primary else "secondary"))

__all__ = ["link_action", "mutation_action", "modal_action"]
```

#### Step 3 — Create `app/core/action_serialization.py`
Not timeline-specific — general serialization utility. Explicit include list prevents future `ActionDescriptor` fields from leaking into embedded dicts.

```python
from typing import Any
from app.core.action_schemas import ActionDescriptor

_STABLE_FRONTEND_FIELDS = frozenset({
    "key", "label", "type", "method", "endpoint", "route",
    "confirm", "confirm_title", "confirm_message",
    "variant", "payload_schema", "task_id",
})

def dump_action_descriptor(action: ActionDescriptor) -> dict[str, Any]:
    return action.model_dump(include=_STABLE_FRONTEND_FIELDS, exclude_none=True)

__all__ = ["dump_action_descriptor"]
```

### Stage 2 — Work Queue Update

#### Step 4 — Update `app/work_queue/schemas/work_queue.py`
Replace inline `WorkQueueAction` definition with an alias. No other work_queue schema changes.

```python
from app.core.action_schemas import ActionDescriptor
WorkQueueAction = ActionDescriptor
```

**WorkQueue wire shape check**: frontend `workQueueActionSchema` has `type` and `payload_schema` as optional fields — `ActionDescriptor` always emits `type` (required). Frontend zod schema accepts extra fields via `.optional()` — no breakage. New fields like `disabled`/`disabled_reason` are absent from domain actions (defaults) — safe.

#### Step 5 — Update `app/work_queue/services/actions.py`
Replace inline helper definitions with imports. Alias names preserve private-looking callers inside the file.

```python
from app.core.action_builders import link_action as _link, mutation_action as _mutation, modal_action as _modal
```

All other work_queue functions (`task_actions`, `source_actions`, etc.) unchanged.

### Stage 3 — Domain Action Rewrites

#### Step 6 — Rewrite `app/actions/binder_actions.py`
Return type: `list[ActionDescriptor]`. Import `mutation_action`. Direct enum comparison (drop `_value()`).

Actions:
- `ready`: `mutation_action(..., confirm_title="אישור סימון כמוכן לאיסוף", confirm_message="האם לסמן את הקלסר כמוכן לאיסוף?")`
- `revert_ready`: `mutation_action(..., confirm_title="ביטול סטטוס מוכן לאיסוף", confirm_message="האם לבטל את הסימון...")`
- `return`: `mutation_action(..., confirm_title="אישור החזרת קלסר", confirm_message="אנא הזן את שם האדם שאסף את הקלסר.", payload_schema="requires_input")`

Note: binder `return` action in frontend goes through `BindersPage.tsx` dedicated dialog (`confirmReturnForId`), not `executeAction`. `payload_schema="requires_input"` is informational — no frontend behavior change needed.

Remove all `ActionContract`, `build_action`, `build_confirm`, `_generate_action_id`, `_value` imports.

#### Step 7 — Rewrite `app/actions/charge_actions.py`
Return type: `list[ActionDescriptor]`. All `build_action` → `mutation_action`.

- `cancel_charge`: `mutation_action(..., confirm_title="אישור ביטול חיוב", confirm_message="האם לבטל את החיוב?", variant="danger")`
- `issue_charge`: plain `mutation_action`
- `delete_charge`: `mutation_action(method="delete", variant="danger", confirm_title=..., confirm_message=...)`
- `mark_paid`: `mutation_action(confirm_title=..., confirm_message=...)`

**UX change**: `confirm_label="אשר ביטול"` dropped. Frontend substitutes default `"אישור"`.

#### Step 8 — Rewrite `app/actions/business_actions.py`
Return type: `list[ActionDescriptor]`. Payload dict dropped → `payload_schema="simple"`.

Confirmed safe: `freeze`/`activate` are in `HIDDEN_ACTION_KEYS` (filtered before render). `close` goes through `mapActions` but `ClientBusinessesCard` uses its own mutation — payload from `available_actions` is never consumed via `executeAction`.

- `freeze`: `mutation_action(..., payload_schema="simple", confirm_title=..., confirm_message=...)`
- `close`: `mutation_action(..., payload_schema="simple", confirm_title=..., confirm_message=...)`
- `activate`: `mutation_action(..., payload_schema="simple")` (no confirm)

**UX change**: `confirm_label="הקפאה"` on freeze dropped. Frontend substitutes `"אישור"`.

#### Step 9 — Rewrite `app/actions/vat_report_actions.py`
Return type: `list[ActionDescriptor]`. All `build_action` → `mutation_action`. Direct enum comparison.

- `materials_complete`, `add_invoice`, `ready_for_review`, `file_vat_return`: plain mutations
- `send_back`: `mutation_action(..., confirm_title="החזרה לתיקון", confirm_message="יש לציין הערה לפני החזרת התיק לתיקון.")`

#### Step 10 — Rewrite `app/actions/report_deadline_actions.py`
Return type: `list[ActionDescriptor]`. `amend` and `submit` are plain mutations, no confirm, no payload.

#### Step 11 — Trim `app/actions/action_helpers.py`
Remove: `ActionContract` TypedDict, `_generate_action_id`, `_value`, `_validate_confirm`.
Keep: `build_action` (return type → `dict[str, Any]`), `build_confirm`, `ActionConfirm` TypedDict, `ConfirmInput` TypedDict, `HttpMethod` alias.
Update `__all__`.

#### Step 12 — Rename `app/actions/action_contracts.py` → `app/actions/action_registry.py`
Add docstring. Remove `build_action` re-export.

```python
"""Action registry: aggregates domain action factories. Import from here, not individual modules."""
from app.actions.binder_actions import get_binder_actions
from app.actions.business_actions import get_business_actions
from app.actions.charge_actions import get_charge_actions
from app.actions.report_deadline_actions import get_annual_report_actions
from app.actions.vat_report_actions import get_vat_work_item_actions
```

Grep all import sites of `action_contracts` and update to `action_registry`:
```bash
rg "action_contracts" app/ tests/ -l
```
Expected: `binder_list_service.py`, `client_business_service.py`, possibly others.

### Stage 4 — Schema Field Updates

#### Step 13 — Update `available_actions` field type in 5 response schemas
Change `list[dict]` → `list[ActionDescriptor]`. Add `from app.core.action_schemas import ActionDescriptor`.

Files:
- `app/binders/schemas/binder.py` — `BinderResponse.available_actions`
- `app/charge/schemas/charge.py` — `ChargeResponse.available_actions` + `ChargeResponseSecretary.available_actions`
- `app/businesses/schemas/business_schemas.py` — `BusinessResponse.available_actions`
- `app/vat_reports/schemas/vat_report.py` — `VatWorkItemResponse.available_actions`
- `app/annual_reports/schemas/annual_report_responses.py` — `AnnualReportResponse.available_actions`

#### Step 14 — Update timeline event builders
`app/timeline/services/timeline_binder_event_builders.py` and `timeline_charge_event_builders.py`:

```python
from app.core.action_schemas import ActionDescriptor
from app.core.action_serialization import dump_action_descriptor

def _attach_actions(event: dict, actions: list[ActionDescriptor]) -> dict:
    event["available_actions"] = [dump_action_descriptor(a) for a in actions]
    return event
```

### Stage 5 — Frontend Mapping Layer

#### Step 15 — Update `src/lib/actions/types.ts`
`BackendAction` updated to accept both old nested confirm (dashboard) and new flat shape (domain actions). `id` optional, `payload` optional.

```typescript
export interface BackendAction {
  id?: string | null
  key: string
  label: string
  method: ActionMethod
  endpoint: string
  payload?: Record<string, unknown> | null
  payload_schema?: 'none' | 'simple' | 'requires_input'
  // New flat confirm fields (domain actions post-migration)
  confirm?: boolean | BackendActionConfirm | null
  confirm_title?: string | null
  confirm_message?: string | null
  variant?: 'primary' | 'secondary' | 'danger' | null
  // Dashboard-only enrichment (untyped in ActionDescriptor)
  binder_id?: number | null
  charge_id?: number | null
  client_id?: number | null
  client_name?: string | null
  binder_number?: string | null
  category?: string | null
  due_label?: string | null
  description?: string | null
  urgency?: 'overdue' | 'upcoming' | null
  due_date?: string | null
}
```

#### Step 16 — Update `src/lib/actions/mapActions.ts`
`mapConfirm` handles both shapes. `uiKey`/`id` fall back to `key` when `id` absent.

```typescript
const mapConfirm = (action: BackendAction): ActionCommand['confirm'] => {
  // New flat shape (domain actions post-migration)
  if (typeof action.confirm === 'boolean' && action.confirm) {
    return {
      title: action.confirm_title ?? 'אישור פעולה',
      message: action.confirm_message ?? 'האם להמשיך?',
      confirmLabel: 'אישור',
      cancelLabel: 'ביטול',
      inputs: undefined,
    }
  }
  // Legacy nested shape (dashboard only — excluded from migration)
  if (action.confirm && typeof action.confirm === 'object') {
    const c = action.confirm as BackendActionConfirm
    return {
      title: c.title,
      message: c.message,
      confirmLabel: c.confirm_label,
      cancelLabel: c.cancel_label,
      inputs: c.inputs,
    }
  }
  return undefined
}

export const mapActions = (actions: BackendAction[] | null | undefined): ActionCommand[] => {
  if (!Array.isArray(actions)) return []
  return actions
    .filter((action) => !HIDDEN_ACTION_KEYS.has(action.key))
    .map((action) => {
      if (!action.endpoint) return null
      return {
        key: action.key,
        uiKey: action.id ?? action.key,
        id: action.id ?? action.key,
        label: action.label,
        method: action.method,
        endpoint: action.endpoint,
        payload: action.payload ?? undefined,
        confirm: mapConfirm(action),
        clientName: action.client_name ?? null,
        binderNumber: action.binder_number ?? null,
        category: action.category ?? null,
        dueLabel: action.due_label ?? null,
        description: action.description ?? null,
        urgency: action.urgency ?? null,
        dueDate: action.due_date ?? null,
      } as ActionCommand
    })
    .filter((a): a is ActionCommand => Boolean(a))
}
```

### Stage 6 — Tests

#### Step 17 — Add `tests/core/test_action_builders.py`
Unit tests for builder output invariants.

```python
def test_mutation_action_requires_endpoint_in_output():
    action = mutation_action("cancel", "ביטול", "/things/1/cancel")
    assert action.endpoint == "/things/1/cancel"
    assert action.type == "mutation"
    assert action.method == "post"

def test_link_action_requires_route_in_output():
    action = link_action("open", "פתח", "/clients/5")
    assert action.route == "/clients/5"
    assert action.type == "link"

def test_modal_action_sets_type():
    action = modal_action("edit", "ערוך", task_id=3)
    assert action.type == "modal"
    assert action.task_id == 3

def test_mutation_action_confirm_flag_set_when_title_provided():
    action = mutation_action("del", "מחק", "/x", confirm_title="אישור", confirm_message="?")
    assert action.confirm is True
    assert action.confirm_title == "אישור"

def test_mutation_action_payload_schema_typed():
    action = mutation_action("freeze", "הקפא", "/businesses/1", payload_schema="simple")
    assert action.payload_schema == "simple"
```

#### Step 18 — Add `tests/actions/test_action_serialization.py`
One serialization shape test per migrated domain. Tests `dump_action_descriptor` output.

```python
from types import SimpleNamespace
from app.actions.binder_actions import get_binder_actions
from app.actions.charge_actions import get_charge_actions
from app.actions.business_actions import get_business_actions
from app.actions.vat_report_actions import get_vat_work_item_actions
from app.actions.report_deadline_actions import get_annual_report_actions
from app.core.action_serialization import dump_action_descriptor
from app.binders.models.binder import BinderStatus
from app.charge.models.charge import ChargeStatus
from app.businesses.models.business import BusinessStatus
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.users.models.user import UserRole

def test_binder_ready_serializes_correct_frontend_shape():
    binder = SimpleNamespace(id=10, status=BinderStatus.IN_OFFICE)
    actions = get_binder_actions(binder)
    dumped = dump_action_descriptor(actions[0])
    assert dumped["key"] == "ready"
    assert dumped["method"] == "post"
    assert dumped["endpoint"] == "/binders/10/ready"
    assert dumped["confirm"] is True
    assert dumped["confirm_title"] == "אישור סימון כמוכן לאיסוף"
    assert "id" not in dumped
    assert "payload" not in dumped

def test_binder_return_signals_requires_input():
    binder = SimpleNamespace(id=11, status=BinderStatus.READY_FOR_PICKUP)
    actions = get_binder_actions(binder)
    ret = next(a for a in actions if a.key == "return")
    dumped = dump_action_descriptor(ret)
    assert dumped["payload_schema"] == "requires_input"
    assert "inputs" not in dumped

def test_charge_cancel_serializes_correct_frontend_shape():
    charge = SimpleNamespace(id=20, status=ChargeStatus.DRAFT)
    actions = get_charge_actions(charge)
    cancel = next(a for a in actions if a.key == "cancel_charge")
    dumped = dump_action_descriptor(cancel)
    assert dumped["confirm_title"] == "אישור ביטול חיוב"
    assert dumped["variant"] == "danger"
    assert "confirm_label" not in dumped

def test_business_freeze_serializes_payload_schema():
    business = SimpleNamespace(id=5, client_id=9, status=BusinessStatus.ACTIVE)
    actions = get_business_actions(business, user_role=UserRole.ADVISOR)
    freeze = next(a for a in actions if a.key == "freeze")
    dumped = dump_action_descriptor(freeze)
    assert dumped["payload_schema"] == "simple"
    assert "payload" not in dumped

def test_vat_send_back_serializes_confirm():
    item = SimpleNamespace(id=3, status=VatWorkItemStatus.READY_FOR_REVIEW)
    actions = get_vat_work_item_actions(item, user_role=UserRole.ADVISOR)
    send_back = next(a for a in actions if a.key == "send_back")
    dumped = dump_action_descriptor(send_back)
    assert dumped["confirm"] is True
    assert dumped["confirm_title"] == "החזרה לתיקון"

def test_annual_report_submit_serializes_correct_endpoint():
    actions = get_annual_report_actions(report_id=8, status="not_started")
    submit = next(a for a in actions if a.key == "submit")
    dumped = dump_action_descriptor(submit)
    assert dumped["endpoint"] == "/annual-reports/8/submit"
    assert "id" not in dumped
```

#### Step 19 — Update domain action tests (attribute access)

**`tests/actions/test_binder_actions.py`**:
- `action["key"]` → `action.key`
- Remove `actions[1]["confirm"]["inputs"][0]["name"]` assertion
- Replace: `assert actions[1].payload_schema == "requires_input"` and `assert actions[1].confirm is True`

**`tests/actions/test_charge_actions.py`**:
- Remove `cancel_action["confirm"]["confirm_label"] == "אשר ביטול"` (field dropped)
- `action.key`, `action.confirm is True`, `action.confirm_title == "אישור ביטול חיוב"`

**`tests/actions/test_business_actions.py`**:
- `actions[0].payload_schema == "simple"` replaces `actions[0]["payload"]`
- Remove `actions[1]["id"]` assertion
- `actions[0].endpoint` replaces dict access

**`tests/actions/test_vat_report_actions.py`** and **`test_report_deadline_actions.py`**: attribute access throughout.

**`tests/actions/test_action_contracts.py`** → rename to `test_action_registry.py`, update import.

#### Step 20 — Update timeline tests

**`tests/timeline/service/test_timeline_event_builders.py`**:
- `ready_action["confirm"]["title"]` → `ready_action["confirm_title"]`
- `ready_action["confirm"] is not None` → `ready_action["confirm"] is True`

**`tests/timeline/service/test_timeline_event_builders_additional.py`**:
- `mark_paid_action["confirm"]["title"]` → `mark_paid_action["confirm_title"]`
- Dict access on other fields remains valid (serialized via `dump_action_descriptor`)

---

## Files Changed

**New backend files:**
- `app/core/action_schemas.py`
- `app/core/action_builders.py`
- `app/core/action_serialization.py`
- `tests/core/test_action_builders.py`
- `tests/actions/test_action_serialization.py`

**Modified backend:**
- `app/work_queue/schemas/work_queue.py` (WorkQueueAction = ActionDescriptor alias)
- `app/work_queue/services/actions.py` (import renamed builders)
- `app/actions/binder_actions.py` (rewrite)
- `app/actions/charge_actions.py` (rewrite)
- `app/actions/business_actions.py` (rewrite)
- `app/actions/vat_report_actions.py` (rewrite)
- `app/actions/report_deadline_actions.py` (rewrite)
- `app/actions/action_helpers.py` (trim — keep build_action/build_confirm)
- All import sites of `action_contracts` → `action_registry`
- `app/binders/schemas/binder.py`, `app/charge/schemas/charge.py`, `app/businesses/schemas/business_schemas.py`, `app/vat_reports/schemas/vat_report.py`, `app/annual_reports/schemas/annual_report_responses.py`
- `app/timeline/services/timeline_binder_event_builders.py`
- `app/timeline/services/timeline_charge_event_builders.py`
- `tests/actions/test_binder_actions.py`, `test_charge_actions.py`, `test_business_actions.py`, `test_vat_report_actions.py`, `test_report_deadline_actions.py`
- `tests/actions/test_action_contracts.py` → `test_action_registry.py`
- `tests/timeline/service/test_timeline_event_builders.py`
- `tests/timeline/service/test_timeline_event_builders_additional.py`

**Renamed backend:**
- `app/actions/action_contracts.py` → `app/actions/action_registry.py`

**Modified frontend:**
- `src/lib/actions/types.ts`
- `src/lib/actions/mapActions.ts`

**Do NOT touch:**
- `app/actions/obligation_orchestrator.py`
- `app/dashboard/services/_quick_actions_helpers.py`
- All dashboard frontend files
- `src/features/binders/pages/BindersPage.tsx` (return dialog is custom, not via executeAction)

---

## Stage Reporting Protocol

After completing each stage, stop and produce this summary before continuing:

```
WU-19 STAGE [N] COMPLETE
=========================
Stage: [stage name]
Steps completed: [e.g. Step 1, Step 2]

Files created:
- [file path]

Files modified:
- [file path] — [what changed]

Files deleted/renamed:
- [old path] → [new path]

Test result: [PASS / FAIL + details]
Typecheck: [PASS / FAIL / N/A]

Notes: [anything unexpected, decisions made, gaps found]

Remaining stages: [list]
```

Do not continue to the next stage until explicit approval is received.

---

## Verification

```bash
# Backend — action + builder suite
JWT_SECRET=test-secret pytest -q tests/actions/ tests/core/

# Backend — timeline
JWT_SECRET=test-secret pytest -q tests/timeline/

# Backend — all affected domains
JWT_SECRET=test-secret pytest -q tests/binders/ tests/charge/ tests/businesses/ tests/vat_reports/ tests/annual_reports/ tests/work_queue/

# Frontend typecheck
cd ../frontend && npm run typecheck
```

Manual smoke: trigger a binder "ready" action, a charge cancel, and a VAT send-back — verify confirm dialogs appear with Hebrew titles and correct behavior.
