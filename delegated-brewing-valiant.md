# Binder Domain Alignment Plan

## Context

The Binder domain was implemented with several incorrect assumptions relative to the domain definitions document (`app/binders/binder_domain_definitions.md`). This plan aligns the full stack — models, migrations, services, API, and frontend — to the correct domain model.

Key problems being fixed:
- Status model conflates "full binder" and "ready for pickup" — missing `CLOSED_IN_OFFICE`
- `is_full` flag is a redundant second source of truth for status
- Binder number uses DB PK (`Client.id`) instead of an office client number
- Reporting period on material rows is free text in `description` — must be structured fields
- `period_start` on binder is caller-supplied — must be derived from first material
- No grouped handover model for multi-binder return events
- No intake edit capability or field-level audit trail
- No old-period fallback-to-active-binder-with-note logic
- No `vat_report_id` linkage on material rows
- Auto-binder on client registration violates period_start semantics

## Review Status

Reviewed against the current worktree on 2026-04-18.

- Done: T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22, T23, T24, T31
- Partial: none
- Pending: T25, T26, T27, T28, T29, T30

---

## Phase 1 — Client Model: Add `office_client_number`

### T1 — Add `office_client_number` to `Client` model
**Status:** done

**File:** `app/clients/models/client.py`
- Add `office_client_number = Column(Integer, nullable=True, unique=True, index=True)`
- Nullable for backward compat; existing rows get NULL
- Must be unique among non-deleted clients (partial unique index)

**File:** `app/clients/schemas/client.py`, `app/clients/schemas/client_create.py` (check actual schema filenames)
- Add `office_client_number: Optional[int] = None` to request and response schemas

**File:** `app/clients/repositories/client_repository.py`
- Accept `office_client_number` in `create()`

**Blocker:** None. Must complete before T13.

---

## Phase 2 — Binder Status Model

### T2 — Add `CLOSED_IN_OFFICE` to `BinderStatus` enum
**Status:** done

**File:** `app/binders/models/binder.py`
```python
class BinderStatus(str, PyEnum):
    IN_OFFICE = "in_office"
    CLOSED_IN_OFFICE = "closed_in_office"
    READY_FOR_PICKUP = "ready_for_pickup"
    RETURNED = "returned"
```
- Update `RETURNED_STATUS_VALUE` reference if it checks by equality
- Update partial index on `binder_number` uniqueness: exclude `IN_OFFICE` only (open active binder is the only one that should be unique per client — `CLOSED_IN_OFFICE` binders have already been superseded)

**Blocker:** None. Must complete before T5, T7, T8.

### T3 — Remove `is_full` from `Binder` model
**Status:** done

**File:** `app/binders/models/binder.py`
- Delete `is_full` column

**File:** `app/binders/repositories/binder_repository.py`
- `get_active_by_client`: change filter from `is_full.is_(False)` → `status == IN_OFFICE`
- `map_active_by_clients`: same change
- `create()`: remove `is_full` kwarg

**File:** `scripts/seed_fake_data_lib/domains/binders.py`
- Remove `is_full` usage from seed data

**Blocker:** T2 must be complete first (status replaces `is_full`).

---

## Phase 3 — Material Row: Structured Reporting Period + VAT Linkage

### T4 — Add structured period fields and `vat_report_id` to `BinderIntakeMaterial`
**Status:** done

**File:** `app/binders/models/binder_intake_material.py`
```python
period_year = Column(Integer, nullable=True)        # nullable for legacy rows
period_month_start = Column(Integer, nullable=True)  # 1–12
period_month_end = Column(Integer, nullable=True)    # 1–12; = period_month_start for monthly
vat_report_id = Column(Integer, ForeignKey("vat_reports.id"), nullable=True, index=True)
```
- `description` stays as optional free-text note only (no period semantics)
- Add index on `vat_report_id`

**Blocker:** None. Must complete before T9, T11, T14.

---

## Phase 4 — New Models

### T5 — Add `BinderHandover` and `binder_handover_binders` association
**Status:** done

**New file:** `app/binders/models/binder_handover.py`
```python
class BinderHandover(Base):
    __tablename__ = "binder_handovers"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    received_by_name = Column(String, nullable=False)
    handed_over_at = Column(Date, nullable=False)
    until_period_year = Column(Integer, nullable=False)
    until_period_month = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
```

Association table `binder_handover_binders`:
```python
class BinderHandoverBinder(Base):
    __tablename__ = "binder_handover_binders"
    id = Column(Integer, primary_key=True)
    handover_id = Column(Integer, ForeignKey("binder_handovers.id"), nullable=False, index=True)
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=False, index=True)
```

**Blocker:** T2 must be complete (RETURNED status used in handover service). Must complete before T16.

### T6 — Add `BinderIntakeEditLog` model
**Status:** done

**New file:** `app/binders/models/binder_intake_edit_log.py`
```python
class BinderIntakeEditLog(Base):
    __tablename__ = "binder_intake_edit_logs"
    id = Column(Integer, primary_key=True)
    intake_id = Column(Integer, ForeignKey("binder_intakes.id"), nullable=False, index=True)
    field_name = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=utcnow, nullable=False)
```

**Blocker:** Must complete before T17.

---

## Phase 5 — Migrations

### T7 — Migration: add `office_client_number` to `clients`
**Status:** done

- Autogenerate from T1 changes
- Review: unique partial index on `office_client_number` where `deleted_at IS NULL`

### T8 — Migration: add `CLOSED_IN_OFFICE` to enum, add structured period fields, add new tables, remove `is_full`
**Status:** done

**⚠️ RISKY — multi-step migration. Must be split into sub-steps:**

Step A: Add `closed_in_office` to `binderstatus` PostgreSQL enum (`ALTER TYPE`)

Step B: Add `period_year`, `period_month_start`, `period_month_end`, `vat_report_id` to `binder_intake_materials`

Step C: Create `binder_handovers`, `binder_handover_binders`, `binder_intake_edit_logs` tables

Step D: Data migration — for all rows where `is_full=True`, set `status = 'closed_in_office'`

Step E: Drop `is_full` column from `binders`

Step F: Backfill `period_year`/`period_month_start`/`period_month_end` from `description` where parseable via `parse_period_to_date()`. Mark unresolved rows by leaving period fields NULL — do NOT invent values.

**Alembic file:** one migration file `0009_binder_domain_alignment.py`

Update `alembic/README` after migration.

---

## Phase 6 — `period_start` Derivation + Onboarding

### T9 — Make `Binder.period_start` nullable; derive from first material
**Status:** done

**File:** `app/binders/models/binder.py`
- Change `period_start = Column(Date, nullable=True)`

**File:** `app/binders/services/binder_intake_service.py`
- In `receive()`: after creating a new binder, set `binder.period_start` from the first material's `period_year` / `period_month_start` (first day of that month)
- If no materials provided to a new binder (onboarding flow), leave `period_start = None`

**File:** `app/binders/repositories/binder_repository.py`
- All sort/filter queries on `period_start` must handle `NULL` gracefully (NULLs last in sort)

**Blocker:** T4 (structured period fields must exist on material). T8 Step E must run.

### T10 — Redesign / remove onboarding auto-binder creation
**Status:** done

**File:** `app/binders/services/client_onboarding_service.py`
- Remove `create_initial_binder` call OR change it to create a placeholder binder with `period_start=None` and `status=IN_OFFICE`, making it explicit this is an empty logistics placeholder

**File:** `app/clients/services/client_service.py` (or wherever `create_initial_binder` is called)
- Remove or gate the call

**File:** `app/clients/constants.py`
- Remove `AUTO_BINDER_SEQUENCE`, `AUTO_BINDER_INITIAL_STATUS`, `AUTO_BINDER_STATUS_LOG_OLD_VALUE`, `AUTO_BINDER_STATUS_LOG_NOTES` if no longer used

**Blocker:** T9 (period_start nullable must be in place first).

---

## Phase 7 — Binder Number Generation

### T11 — Use `office_client_number` for binder number
**Status:** done

**File:** `app/binders/services/binder_intake_service.py`
- `_build_binder_number(client, seq)`: use `client.office_client_number` instead of `client_id`
- Requires loading the `Client` object (already done in `receive()`)

**File:** `app/binders/services/client_onboarding_service.py`
- Update binder number construction if onboarding flow is kept

**File:** `app/binders/repositories/binder_repository.py`
- `count_all_by_client`: unchanged — still counts all binders for sequence

**⚠️ RISKY:** If `office_client_number` is NULL for an existing client, binder number generation will fail. Must handle: raise a clear error if `office_client_number` is not set when creating a binder.

**Blocker:** T1 (field must exist), T8 Step E.

---

## Phase 8 — Transition Validators

### T12 — Update transition validators for new status
**Status:** done

**File:** `app/binders/services/binder_helpers.py`
- `validate_ready_transition`: allow from `IN_OFFICE` **and** `CLOSED_IN_OFFICE`
- `validate_return_transition`: allow from `READY_FOR_PICKUP` only (unchanged)
- `validate_revert_ready_transition`: allow from `READY_FOR_PICKUP` only (unchanged)
- Remove `parse_period_to_date` or keep as legacy-only utility (no longer used for closing period)
- Update `open_new_binder=True` path in `binder_intake_service.py`: set `status=CLOSED_IN_OFFICE` instead of `is_full=True`

**Blocker:** T2.

---

## Phase 9 — Old-Period Material Logic

### T13 — Implement old-period fallback-to-active-binder-with-note
**Status:** done

**File:** `app/binders/services/binder_intake_service.py`
- In `receive()`, after determining target binder:
  - If the material row's period is older than the current active binder's `period_start`, attach to active binder but require a note (`notes` field on the intake must be non-empty, or add `old_period_note` to the material row)
  - This is enforced at service layer, not UI only
- Raise `AppError` if old-period material is inserted with no note

**Review note:** completed in `binder_intake_service.py` by selecting the target binder before any close-and-open flow runs:
- if a matching older `CLOSED_IN_OFFICE` binder exists for the material period, the intake is attached there
- otherwise the intake stays on the current active binder and still requires a note for old-period material
- `open_new_binder=True` no longer forces a new binder for old-period intake

**Blocker:** T4 (structured period fields must exist to compare periods).

---

## Phase 10 — Intake Edit + Audit Trail

### T14 — Add intake edit service + audit trail
**Status:** done

**File:** `app/binders/services/binder_intake_service.py` (or new `binder_intake_edit_service.py` if file exceeds 150 lines)
- Add `edit_intake()` method:
  - Accepts: `intake_id`, `actor_id`, `patch` dict of fields to change
  - For each changed field: write a `BinderIntakeEditLog` record (old/new value)
  - If `client_id` changes (intake moved to another client):
    - Validate new client exists
    - Validate every linked `business_id` belongs to new client
    - Validate every linked `annual_report_id` belongs to new client
    - Validate every linked `vat_report_id` belongs to new client
    - Move intake to a binder belonging to new client
    - Raise `AppError` if any FK validation fails

**New file:** `app/binders/repositories/binder_intake_edit_log_repository.py`
- `append(intake_id, field_name, old_value, new_value, changed_by)`

**Review note:** completed in `binder_intake_edit_service.py`:
- `edit_intake(patch)` now handles both direct intake edits and cross-client transfer semantics
- `edit_intake_transfer()` remains as a compatibility wrapper over `edit_intake()`
- linked `business_id`, `annual_report_id`, and `vat_report_id` replacements are validated against the target client and logged individually at field level
- client-level move is also logged via a `client_id` audit entry, and the intake is moved to a binder belonging to the target client

**Blocker:** T6 (model must exist).

---

## Phase 11 — Grouped Handover Service + API

### T15 — Add `BinderHandoverRepository`
**Status:** done

**New file:** `app/binders/repositories/binder_handover_repository.py`
- `create(client_id, received_by_name, handed_over_at, until_period_year, until_period_month, binder_ids, notes, created_by)`
- `list_by_client(client_id)`
- `get_by_id(handover_id)`

**Blocker:** T5.

### T16 — Add `BinderHandoverService`
**Status:** done

**New file:** `app/binders/services/binder_handover_service.py`
- `create_handover(client_id, binder_ids, received_by_name, handed_over_at, until_period_year, until_period_month, notes, actor_id)`:
  - Validate all `binder_ids` belong to `client_id`
  - Validate all binders are in `READY_FOR_PICKUP` status
  - Set each binder's status → `RETURNED`, set `returned_at`, set `pickup_person_name = received_by_name`
  - Write `BinderStatusLog` for each binder
  - Create `BinderHandover` + `BinderHandoverBinder` rows
  - Return handover record

**Blocker:** T15, T2.

### T17 — Add handover schemas
**Status:** done

**File:** `app/binders/schemas/binder.py` (or new `app/binders/schemas/binder_handover.py`)
```python
class BinderHandoverRequest(BaseModel):
    client_id: int
    binder_ids: list[int]
    received_by_name: str
    handed_over_at: date
    until_period_year: int
    until_period_month: int
    notes: Optional[str] = None

class BinderHandoverResponse(BaseModel):
    id: int
    client_id: int
    received_by_name: str
    handed_over_at: date
    until_period_year: int
    until_period_month: int
    binder_ids: list[int]
    created_at: ApiDateTime
```

**Blocker:** T5.

### T18 — Add handover API endpoint
**Status:** done

**File:** `app/binders/api/binders_receive_return.py` (or new `binders_handover.py`)
- `POST /api/v1/binders/handover` → `BinderHandoverService.create_handover()`
- Role: `ADVISOR` and `SECRETARY`

**Blocker:** T16, T17.

---

## Phase 12 — Bulk Mark-Ready

### T19 — Add bulk mark-ready service method
**Status:** done

**File:** `app/binders/services/binder_service.py`
- `mark_ready_bulk(client_id, until_period_year, until_period_month, user_id)`:
  - Fetch all binders for client in `IN_OFFICE` or `CLOSED_IN_OFFICE` status
  - Filter: binder's latest material period ≤ until_period cutoff
  - Transition each → `READY_FOR_PICKUP`
  - Write status log for each
  - Return list of updated binders

### T20 — Add bulk mark-ready API endpoint
**Status:** done

**File:** `app/binders/api/binders_receive_return.py`
- `POST /api/v1/binders/mark-ready-bulk`
- Request: `{ client_id, until_period_year, until_period_month }`
- Response: list of updated `BinderResponse`

**Blocker:** T12, T19.

---

## Phase 13 — Schema Updates (Backend)

### T21 — Update `BinderIntakeMaterialRequest` and `BinderIntakeMaterialResponse`
**Status:** done

**File:** `app/binders/schemas/binder.py`
- `BinderIntakeMaterialRequest`: add `period_year: int`, `period_month_start: int`, `period_month_end: int`, `vat_report_id: Optional[int] = None`. Keep `description: Optional[str]`.
- `BinderIntakeMaterialResponse`: add same fields.
- Remove `period_start` from `BinderReceiveRequest`.

**Blocker:** T4.

### T22 — Update `BinderListCounters` to include `closed_in_office`
**Status:** done

**File:** `app/binders/schemas/binder.py`
- `BinderListCounters` dict key `"closed_in_office"` added to counters
**File:** `app/binders/services/binder_list_service.py`
- `_build_binder_counters()`: add `BinderStatus.CLOSED_IN_OFFICE` count

**Blocker:** T2.

---

## Phase 14 — Cross-Domain Cleanup

### T23 — Update search service `is_full` → status check
**Status:** done

**File:** `app/search/services/search_service.py`
- `map_active_by_clients()` usage: already goes through repo; repo change in T3 covers this

### T24 — Update signals / dashboard if needed
**Status:** done

**Files:** `app/binders/services/operational_signals_builder.py`, `app/dashboard/services/`
- Verify no direct `is_full` references remain after T3 (agent confirmed: not used outside binder repo)

---

## Phase 15 — Frontend

### T25 — Add `closed_in_office` to binder status labels and variants
**Status:** pending

**File:** `src/utils/enums.ts`
- Add `closed_in_office: "סגור במשרד"` to `BINDER_STATUS_LABELS`

**File:** `src/features/binders/constants.ts`
- Add `closed_in_office: "warning"` to `BINDER_STATUS_VARIANTS`

### T26 — Update `BinderListCounters` type
**Status:** pending

**File:** `src/features/binders/types.ts`
- Add `closed_in_office: number` to `BinderListCounters` interface

### T27 — Update `BinderResponse` type: remove `is_full`, update `period_start`
**Status:** pending

**File:** `src/features/binders/types.ts`
- Remove `is_full: boolean`
- `period_start: string | null` (already nullable — OK)

**File:** `src/features/binders/components/BinderDetailsPanel.tsx`
- Remove `is_full` badge display (lines 30-33)

**File:** `src/features/binders/hooks/useReceiveBinderDrawer.ts`
- Line 106: remove `!b.is_full` check — active binder is now determined by `status === "in_office"` only

### T28 — Update intake form: replace `reporting_period` string with structured period fields
**Status:** pending

**File:** `src/features/binders/schemas.ts`
- Replace `reporting_period: z.string()` with `period_year: z.number()`, `period_month_start: z.number()`, `period_month_end: z.number()`

**File:** `src/features/binders/components/BinderReceivePanel.tsx`
- Replace `reporting_period` free-text/string field with structured year + month range pickers

**File:** `src/features/binders/types.ts`
- `ReceiveBinderPayload.materials[]`: replace `description` period usage with `period_year`, `period_month_start`, `period_month_end`; keep `description` as optional note

**File:** `src/features/binders/components/BinderIntakesSection.tsx`
- Display structured period (year + month range) instead of raw `description`

### T29 — Remove `period_start` from receive payload
**Status:** pending

**File:** `src/features/binders/types.ts`
- Remove `period_start` from `ReceiveBinderPayload` (it's derived server-side now)

**File:** `src/features/binders/schemas.ts`
- Remove `period_start` from receive schema

### T30 — Add handover UI (new feature)
**Status:** pending

**New files:** 
- `src/features/binders/components/BinderHandoverPanel.tsx`
- `src/features/binders/api/contracts.ts`: add `BinderHandoverPayload`, `BinderHandoverResponse` types

This is a new UI flow; scope separately from other tasks.

---

## Phase 16 — Error Codes + Messages

### T31 — Add new error codes and Hebrew messages
**Status:** done

**File:** `app/binders/services/messages.py`
- `BINDER_OLD_PERIOD_NOTE_REQUIRED` — for old-period material without note
- `BINDER_INTAKE_CROSS_CLIENT_VALIDATION_FAILED` — for FK validation on intake transfer
- `BINDER_OFFICE_NUMBER_MISSING` — for binder creation when `office_client_number` is NULL
- `BINDER_HANDOVER_INVALID_BINDERS` — for handover with non-READY binders

---

## Verification

```bash
# Run all binder tests after each phase
JWT_SECRET=test-secret pytest -q tests/binders tests/actions/test_binder_actions.py tests/businesses/api/test_business_binders_api.py tests/regression/test_core_regressions_binders_charges_notifications.py

# Run migrations
APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade head

# Smoke test API
# POST /api/v1/binders/receive — verify period_start is derived
# POST /api/v1/binders/{id}/ready — verify CLOSED_IN_OFFICE → READY_FOR_PICKUP works
# POST /api/v1/binders/handover — verify grouped return creates handover record
# GET /api/v1/binders — verify closed_in_office appears in counters
```

Review run on 2026-04-18:
- `pytest -q tests/binders tests/actions/test_binder_actions.py tests/businesses/api/test_business_binders_api.py tests/regression/test_core_regressions_binders_charges_notifications.py`
- Result: `55 passed` (with one existing pytest config warning about unknown `asyncio_mode`)

---

## Task Ordering Summary (Critical Path)

```
T1 (Client.office_client_number)
  └─ T7 (migration)
       └─ T11 (binder number uses office_client_number)

T2 (CLOSED_IN_OFFICE enum)
  └─ T3 (remove is_full)
  └─ T5 (BinderHandover model)
  └─ T12 (transition validators)
  └─ T22 (counters)

T4 (structured period fields on material)
  └─ T9 (period_start derivation)
  └─ T13 (old-period logic)
  └─ T21 (schema updates)

T6 (BinderIntakeEditLog model)
  └─ T14 (intake edit service)

T5 + T15 (handover model + repo)
  └─ T16 (handover service)
       └─ T17 + T18 (handover schema + API)

All T-backend → T25–T30 (frontend)
```

## Risk Register

| # | Task | Risk | Mitigation |
|---|---|---|---|
| R1 | T11 | `office_client_number` NULL on existing clients blocks binder creation | Raise clear AppError; admin must set field before intake can proceed |
| R2 | T8 | Multi-step migration in single file; SQLite enum change not supported natively | Test each step; use string type for SQLite compat (already the pattern) |
| R3 | T8 Step F | Legacy material rows with non-parseable `description` cannot be backfilled | Leave NULL, flag with comment, do not fabricate |
| R4 | T9 | Nullable `period_start` breaks sort queries that assume non-null | `NULLS LAST` on all sort queries |
| R5 | T14 | Intake-to-new-client transfer is destructive if FK validation is wrong | Wrap in transaction; rollback on any validation failure |
| R6 | T10 | Removing auto-binder on registration may break onboarding flow | Decide explicitly: remove or redesign as placeholder |
