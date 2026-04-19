# Client Domain — Deep Code Review

---

## 1. Critical Issues

### 1.1 `generate_client_obligations` called twice on client creation + inverted docstring
**Files:** `app/clients/services/client_service.py:91-93`, `app/businesses/services/business_service.py:75-79`, `app/actions/obligation_orchestrator.py:47-53`

`ClientService.create_client()` calls `generate_client_obligations(best_effort=False)`. Then `CreateClientService` immediately calls `BusinessService.create_business()`, which calls `generate_client_obligations(best_effort=False)` again — same transaction.

The second call is idempotent (existing records skipped), but wastes two DB round-trips per client creation with no benefit.

The `best_effort` flag semantics are also documented backwards in `obligation_orchestrator.py`:
- Docstring (line 47-49): says `best_effort=False` = suppress errors, continue (update flows)
- Actual code (`if not best_effort: raise`): `best_effort=False` = **raise on error** (strict mode)
- `best_effort=True` = suppress and continue

Both callers use `best_effort=False` (correct/strict), but the inverted docstring is a maintenance hazard — any new caller reading the comment will use the wrong value.

Fix: (1) Remove the duplicate `generate_client_obligations` call from `BusinessService.create_business()` when called during first-business creation. Orchestrate it once from `CreateClientService.create_client()` after both records exist. (2) Fix the docstring in `obligation_orchestrator.py` to correctly describe `best_effort=False` as strict/raise mode.

---

### 1.2 Race condition in `_create_client_with_generated_office_number` + wrong error on failure
**File:** `app/clients/services/client_service.py:122-152`

`get_next_office_client_number()` does `SELECT MAX(office_client_number)` with no row lock. Between that read and `flush()`, a concurrent request can claim the same number. The savepoint/retry loop handles this correctly by catching `IntegrityError` and retrying up to 3 times — that part works.

However: after 3 failed attempts (all `IntegrityError`s on the `office_client_number` unique index), the error raised is `CLIENT_ID_NUMBER_CONFLICT` with a message about a duplicate ID number. The actual failure is a duplicate office client number — wrong code, wrong user-facing message, no way for the frontend to distinguish this from a real ID-number conflict.

Additionally: the partial unique index is on `office_client_number WHERE deleted_at IS NULL`. If a collision happens specifically on the `id_number` unique index (not office number), `IntegrityError` is caught and retried 3 times unnecessarily before raising the same misleading error instead of the `CLIENT.CONFLICT` error that the pre-check should have caught.

Fix: (1) After 3 `IntegrityError` retries, raise a distinct error code (e.g., `OFFICE_NUMBER.CONFLICT`) with a correct Hebrew message. (2) Consider distinguishing which unique constraint caused the `IntegrityError` to avoid masking real ID-number conflicts behind a retry loop.

---

### 1.3 `create_initial_binder` silently skips when `actor_id is None`
**File:** `app/binders/services/client_onboarding_service.py:26-27`

If `actor_id=None`, the function logs a warning and returns without creating the binder. `ClientService.create_client()` does not check the return value and does not raise. The client is created, the binder is silently missing, the audit log is skipped (line 94 in `client_service.py` is guarded by `if actor_id:`). The client is in a broken state — it exists without a binder and without an audit entry.

`actor_id` is `Optional[int]` in the service signature, inherited from Excel import which passes `actor_id=actor_id` (can be `None` if the import endpoint's user resolution fails, though that path is blocked by `require_role`). Still — the code accepts `None` and silently corrupts state.

Fix: Either remove the `actor_id is None` guard in `create_initial_binder` and enforce non-null at the call site, or raise inside `create_initial_binder` instead of returning.

---

### 1.4 `soft_delete` on client does NOT soft-delete related businesses
**File:** `app/clients/api/clients.py:208-209`, `app/clients/services/client_service.py:180-188`

The docstring on the DELETE endpoint literally says: "אינו מוחק את העסקים של הלקוח — יש למחוק אותם בנפרד." This means after a client soft-delete, all their businesses remain active. Other domains that query businesses by `client_id` (charge, binders, vat_reports) will still return data for a deleted client's businesses. This creates ghost data and potential IDOR adjacency (business records for a nominally-deleted client are still served).

This may be intentional. But if so, the restore flow does not re-activate frozen/closed businesses either — it only restores the client record. There is no documented lifecycle rule for what happens to businesses when a client is deleted/restored.

Fix: Document the explicit decision. If deletion should cascade, add `BusinessService.soft_delete_all_by_client()` and call it from `ClientService.delete_client()` inside the same transaction. If not, add a guard in business-query paths that checks `client.deleted_at` before returning results.

---

### 1.5 Excel import bypasses all `CreateClientRequest` validations
**File:** `app/clients/services/client_excel_service.py:68-109`

Excel import calls `CreateClientService.create_client()` directly with only `full_name`, `business_name`, `id_number`, `phone`, `email`. All of these fields are positional — there is no Pydantic validation applied. No `entity_type`, no `vat_reporting_frequency`, no address, no `accountant_name`. These are **required** fields on `CreateClientRequest` (enforced in `require_full_create_payload`).

So the API path enforces strict mandatory fields, but the Excel import silently creates clients with `entity_type=None`, `vat_reporting_frequency=None`, `accountant_name=None`, etc. These clients will fail obligation generation logic (entity_type None = `ClientTypeForReport.INDIVIDUAL`, no VAT deadlines generated), have no binder if `actor_id` is None (same bug as 1.3), and produce incomplete records.

Fix: Either extend the Excel format to include all required fields, or validate each row against `ClientCreateRequest` before passing to the service, collecting `ValidationError` alongside other row errors.

---

### 1.6 `update_client` audit always runs — including when `actor_id=None`
**File:** `app/clients/services/client_service.py:172-177`

`create_client` guards audit with `if actor_id:`. `update_client` has no such guard — it always calls `self._audit.append(performed_by=actor_id, ...)`. If `actor_id=None`, this writes a row with `performed_by=NULL`. The `EntityAuditLogRepository` may or may not allow NULL — if there's a NOT NULL FK constraint on `performed_by`, this is a silent failure or integrity error. If nullable, audit rows with no actor are silently inserted, polluting audit history.

Fix: Guard `self._audit.append(...)` with `if actor_id:` in `update_client`, or enforce non-null `actor_id` at the endpoint level (the PATCH endpoint receives `user: CurrentUser` so actor_id is always present there — the inconsistency is that the service signature allows None).

---

## 2. Logic / Modeling Issues

### 2.1 `CreateClientRequest.require_full_create_payload` duplicates validation from `ClientCreateRequest`
**File:** `app/clients/schemas/client.py:106-135`

`ClientCreateRequest.validate_id_checksum` already validates that `vat_reporting_frequency` is required for non-employee entity types (line 74-76). `CreateClientRequest.require_full_create_payload` re-checks `vat_reporting_frequency is None` unconditionally (line 126-127) — this would reject `EMPLOYEE` clients even if they have `entity_type=EMPLOYEE` and `vat_reporting_frequency=None`, which is valid per the first validator.

Actually `CreateClientRequest.require_full_create_payload` mandates VAT frequency for ALL entity types (line 126-127 has no `entity_type` guard), overriding the per-type logic in `ClientCreateRequest`. These two validators produce inconsistent behavior depending on the order they run. The outer validator is stricter, effectively making `vat_reporting_frequency` mandatory for employees too.

Fix: Remove the blanket `vat_reporting_frequency` check from `CreateClientRequest` and rely on the per-type check in `ClientCreateRequest`. Or document explicitly that employee clients require VAT frequency in full creation.

---

### 2.2 `get_next_office_client_number` includes soft-deleted clients in MAX
**File:** `app/clients/repositories/client_repository.py:206-209`

`SELECT MAX(office_client_number)` has no `deleted_at IS NULL` filter. A deleted client with `office_client_number=50` means the next client gets 51. But the partial unique index `ix_clients_office_client_number_active` only enforces uniqueness among active clients — so number 50 can be reused. The re-use is intentional per the partial index, but the `MAX()` approach means deleted numbers are permanently "wasted" from the sequence, which will cause gaps and confuse staff (the physical label sequence will be non-contiguous).

This may be intentional (never reuse a physical label). But it's undocumented. Fix: Add a comment explaining the explicit decision not to reuse office client numbers, even after deletion.

---

### 2.3 `restore_client` does not regenerate obligations or binder
**File:** `app/clients/services/client_service.py:190-211`

When a client is restored, nothing re-generates obligations (VAT deadlines, annual reports) for the current year, and no binder re-creation logic runs. If the client was deleted in the middle of a tax year, restored clients will have stale/missing obligations. This is a silent gap in the restore lifecycle.

Fix: Call `generate_client_obligations(..., best_effort=True)` inside `restore_client` after the restore, analogous to what creation does.

---

### 2.4 `ClientStatus` on the Client model is unused in business logic
**File:** `app/clients/models/client.py:56`, `app/clients/schemas/client.py:84`

`ClientStatus` (ACTIVE/FROZEN/CLOSED) exists on the `Client` model. `ClientUpdateRequest` exposes `status` as an updatable field. But there is no service-layer validation that enforces status transitions (e.g., can you freeze an already-closed client?). There is also no domain behavior triggered by status change — no cascade to businesses, no effect on which operations are allowed. The status is accepted and persisted but has no behavioral consequence.

Either enforce status transitions and derive downstream behavior from client status, or remove the status field from `ClientUpdateRequest` if status is meant to be derived from business status.

---

### 2.5 `ClientUpdateRequest` allows updating `entity_type` after creation with no cascading guard
**File:** `app/clients/services/client_service.py:160-178`

Changing `entity_type` on an existing client triggers `generate_client_obligations`. But it does not:
- Validate whether existing obligations for the old type are left orphaned
- Warn that previously-generated VAT deadlines for the old type are not removed
- Check whether the client has filed reports under the old type

A client created as `OSEK_PATUR` with 12 months of filed VAT deadlines could be changed to `EMPLOYEE` — the filed deadlines remain, new deadlines are not generated (EMPLOYEE has none), and the annual report type changes silently. No guard exists.

Fix: At minimum, raise a documented domain error or warning when `entity_type` changes on a client with existing filed obligations.

---

### 2.6 `preview-impact` endpoint accepts the full `CreateClientRequest` but only uses two fields
**File:** `app/clients/api/clients.py:61-69`

`preview_creation_impact` validates the entire `CreateClientRequest` schema including mandatory business fields (`opened_at` required). The frontend cannot call this for preview unless it has already filled in all creation fields. This design forces the frontend to validate the full form before computing a preview — which defeats the purpose of a preview endpoint.

Fix: Accept a minimal schema (just `entity_type` and `vat_reporting_frequency`) for the preview endpoint.

---

## 3. Code Quality Issues

### 3.1 `_raise_client_conflict` is a non-method function inside the API module with business-like logic
**File:** `app/clients/api/clients.py:34-53`

This function fetches `conflict_info` by calling `service.get_conflict_info()` and transforms it into schema objects. It's placed at module level in the API file but uses service-layer logic. It should either be a private method on a handler class or moved to a service. Currently it takes `service: ClientService` as an argument, which means the API module is instantiating services in two places per request (once in `create_client`, once passed to `_raise_client_conflict`).

---

### 3.2 `enrich_single` instantiates `BinderOperationsService` per call — N+1 risk in non-list paths
**File:** `app/clients/api/client_enrichment.py:8-14`

`enrich_single` creates a new `BinderOperationsService` per client response. For the list path, `enrich_list` batches correctly. But `enrich_single` is called from `update_client` and `get_client` — one service instantiation per request is fine. However, `create_client` also calls `enrich_single` (line 117), which adds another DB query immediately after creation. The binder was just created and flushed — the query is redundant. The new binder's number is known from the creation result.

Fix: Pass `binder.binder_number` directly to `CreateClientResponse` after creation instead of enriching via DB query.

---

### 3.3 `list` and `count` in `ClientRepository` duplicate filter logic
**File:** `app/clients/repositories/client_repository.py:123-159`

`list()` and `count()` duplicate identical filter construction (search term, status filter). Any change to filtering logic must be applied in both places. Extract a `_build_query(search, status)` helper.

---

### 3.4 `ClientExcelService.__init__` creates a temp directory on every instantiation
**File:** `app/clients/services/client_excel_service.py:26-27`

`mkdir(parents=True, exist_ok=True)` runs on every request. This is a side effect in `__init__` that touches the filesystem unconditionally, even for requests that only import clients (not export). Move directory creation to the methods that actually write files.

---

### 3.5 `import_clients_from_excel` catches bare `Exception`
**File:** `app/clients/services/client_excel_service.py:105-107`

`except Exception as exc: errors.append({"row": row_index, "error": str(exc)})` — broad exception handling converts every possible error (DB connection failure, OOM, programming error) into a user-facing row error. A real infrastructure failure would silently append a meaningless error string to the errors list and continue processing remaining rows against a potentially broken DB session.

Fix: Catch only `ConflictError`, `NotFoundError`, `ValueError`, and `AppError`. Let unexpected exceptions propagate.

---

### 3.6 `create_client_service.py` validates `business_name` with a bare `ValueError`
**File:** `app/clients/services/create_client_service.py:50-51`

`raise ValueError("יש להזין שם עסק")` — a `ValueError` from the service layer will bubble up uncaught (it's not a `ConflictError` or `NotFoundError`), cause a 500, and be swallowed by the global exception handler with no user-facing message. The API does not catch `ValueError`.

Fix: Raise `AppError` or `ValidationError` with a proper code and status 400.

---

### 3.7 `ClientService` has 225 lines — exceeds project 150-line limit
**File:** `app/clients/services/client_service.py`

Project rule: max 150 lines. File is 225 lines. The mutation methods (`create`, `update`, `delete`, `restore`) and query delegation are all in one class.

Fix: Split `create_client` and `_create_client_with_generated_office_number` into `ClientMutationService`, keeping `ClientService` as a thin facade or renaming accordingly.

---

### 3.8 `client_query_service.py` is a thin wrapper with no logic
**File:** `app/clients/services/client_query_service.py`

`ClientQueryService` has 3 methods that are direct pass-throughs to the repository with no business logic added. The only reason it exists is to keep `client_service.py` short. But `client_service.py` already exceeds 150 lines anyway. This abstraction adds indirection without value.

Fix: Either merge `ClientQueryService` back into the service (after splitting the mutation logic out per 3.7), or justify its existence with actual logic.

---

## 4. Recommended Fixes (Priority Order)

### P0 — Data integrity / correctness

**Fix 1.3 — Silent binder skip on null actor_id**
- File: `app/binders/services/client_onboarding_service.py:26-27`
- Issue: `actor_id is None` silently skips binder creation, leaving client in inconsistent state.
- Why: Client exists with no binder. All downstream binder-dependent flows are broken for this client.
- Fix: Replace `return` with `raise ValueError("actor_id נדרש ליצירת קלסר ראשוני")`. Enforce non-null at callers.

**Fix 1.5 — Excel import bypasses required field validation**
- File: `app/clients/services/client_excel_service.py:68-109`
- Issue: Imported clients can have `entity_type=None`, no address, no accountant, etc.
- Why: Creates structurally incomplete client records that break obligation generation.
- Fix: Validate each row via `ClientCreateRequest` schema before passing to service. Collect `ValidationError` as row errors.

**Fix 1.4 — Delete does not cascade to businesses**
- File: `app/clients/services/client_service.py:180-188`
- Issue: Businesses of deleted clients remain active and queryable.
- Why: Ghost data; queries by `client_id` from other domains still return results.
- Fix: Either add `BusinessService.soft_delete_all_by_client(client_id)` inside `delete_client` transaction, or document and enforce that business queries check `client.deleted_at`.

**Fix 2.3 — Restore does not regenerate obligations**
- File: `app/clients/services/client_service.py:190-211`
- Issue: Restored clients have no current-year obligations.
- Why: They are functionally broken for tax workflows.
- Fix: Add `generate_client_obligations(self.db, client_id, entity_type=..., best_effort=True)` after `restore()` call.

---

### P1 — Logic correctness

**Fix 1.1 — Duplicate `generate_client_obligations` call + inverted docstring**
- Files: `app/clients/services/client_service.py:91-93`, `app/businesses/services/business_service.py:75-79`, `app/actions/obligation_orchestrator.py:47-53`
- Issue: Double obligation generation on client creation. Docstring describes `best_effort` semantics in reverse.
- Fix: Remove `generate_client_obligations` from `BusinessService.create_business()`. Move it to `CreateClientService.create_client()` after both records are created, once, `best_effort=False`. Fix docstring to match actual `if not best_effort: raise` behavior.

**Fix 1.2 — Wrong error message on office number conflict**
- File: `app/clients/services/client_service.py:152`
- Issue: `CLIENT_ID_NUMBER_CONFLICT` message on `office_client_number` collision.
- Fix: Raise a distinct error code `OFFICE_NUMBER.CONFLICT` with a correct Hebrew message.

**Fix 2.1 — Duplicate/conflicting VAT validation between `ClientCreateRequest` and `CreateClientRequest`**
- File: `app/clients/schemas/client.py:106-135`
- Issue: `CreateClientRequest` overrides per-type logic from `ClientCreateRequest`.
- Fix: Remove blanket `vat_reporting_frequency` check at line 126-127 from `CreateClientRequest.require_full_create_payload`.

**Fix 2.6 — `preview-impact` requires full creation schema**
- File: `app/clients/api/clients.py:56-69`
- Issue: Preview endpoint rejects requests unless all creation fields are filled.
- Fix: Create `ClientImpactPreviewRequest(entity_type, vat_reporting_frequency)` and use it for this endpoint.

**Fix 3.6 — `ValueError` from service layer causes 500**
- File: `app/clients/services/create_client_service.py:50-51`
- Issue: Bare `ValueError` not caught by API, produces unhandled 500.
- Fix: Replace with `raise AppError("יש להזין שם עסק", "BUSINESS.NAME_REQUIRED", status_code=400)`.

---

### P2 — Code quality / maintainability

**Fix 1.6 — Audit written with null actor_id in `update_client`**
- File: `app/clients/services/client_service.py:172-177`
- Fix: Guard with `if actor_id:` before calling `self._audit.append`.

**Fix 3.7 — `client_service.py` exceeds 150-line limit**
- File: `app/clients/services/client_service.py`
- Fix: Extract `_create_client_with_generated_office_number` + `create_client` into `ClientMutationService`. Keep `ClientService` as thin facade.

**Fix 3.3 — Duplicated filter logic in repository**
- File: `app/clients/repositories/client_repository.py:123-159`
- Fix: Extract `_build_active_query(search, status)` helper used by both `list` and `count`.

**Fix 3.5 — Bare `except Exception` in Excel import**
- File: `app/clients/services/client_excel_service.py:105-107`
- Fix: Catch only domain exceptions. Let infrastructure errors propagate.

**Fix 3.4 — Filesystem side effect in `__init__`**
- File: `app/clients/services/client_excel_service.py:26-27`
- Fix: Move `mkdir` to `export_clients()` and `generate_template()` only.

**Fix 3.2 — Redundant binder DB query after creation**
- File: `app/clients/api/clients.py:116-120`, `app/clients/api/client_enrichment.py:8-14`
- Fix: Pass `binder.binder_number` from creation result directly into `CreateClientResponse` without calling `enrich_single`.
