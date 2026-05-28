## Scope
This file owns only:
- Error-contract audit findings and migration-preparation notes at the time of the audit.

This file must not contain:
- Canonical API contract rules.
- Current implementation behavior unless verified against code.
- Product/domain behavior.

Source of truth: reference

# Error Contract Migration Audit

## Understanding Confirmation

This audit is preparation only. Do not implement the migration in this pass.

Target migration:
- Replace the existing backend error response contract with one canonical shape:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": null,
    "request_id": "..."
  }
}
```

Rules for the implementation pass:
- Do not keep legacy fields.
- Do not add backwards compatibility wrappers.
- Do not support both old and new contracts.
- Do not add workaround parsing.
- Keep responsibility boundaries clear.
- Keep the implementation small and direct.
- Do not change business semantics or status codes unless an existing bug is explicitly found.
- All user-facing messages must remain Hebrew.
- Always include `error.details` in the response body, even when the value is `null`.
- Include `error.request_id` only when a request id is available.
- Do not move old `detail` payloads into `error.details` as-is.
- Normalize details into clean domain-specific structures.
- Do not allow nested legacy keys inside `error.details`: `error`, `detail`, `error_meta`, `status_code`.

## Current Backend Contract

Current centralized implementation:
- `app/core/exceptions.py:23` defines `ErrorResponse`.
- `app/core/exceptions.py:45` defines `_error_json`.
- `app/core/exceptions.py:38` returns top-level `detail`.
- `app/core/exceptions.py:40` returns top-level `error` as a string.
- `app/core/exceptions.py:41` returns `error_meta`.

Current response shape:

```json
{
  "detail": "...",
  "error": "SOME.CODE",
  "error_meta": {
    "type": "SOME.CODE",
    "detail": "...",
    "status_code": 400
  }
}
```

This must be removed completely.

## Backend Implementation Changes

### `app/core/exceptions.py`

Replace the current module-level response builder and handlers.

Locations:
- `app/core/exceptions.py:23-42`
  - Remove `ErrorResponse`.
  - Remove legacy `detail`, string `error`, and `error_meta` generation.
  - Replace with `error_response(...)` returning only the new envelope.

- `app/core/exceptions.py:45-53`
  - Remove `_error_json`.
  - Replace all call sites with `error_response(...)`.

- `app/core/exceptions.py:59-64`
  - Update `AppError` to include `details: Any | None = None`.
  - Preserve `message`, `code`, and `status_code`.

- `app/core/exceptions.py:67-79`
  - Keep `NotFoundError`, `ConflictError`, `ForbiddenError`.
  - Update constructor signatures only if needed to pass optional details cleanly.

- `app/core/exceptions.py:85-90`
  - Replace HTTP exception handler output.
  - Use `http_error_code_for_status(status_code)`.
  - Use Hebrew `exc.detail` only when it is a Hebrew string.
  - Otherwise use `http_error_message_for_status(status_code)`.
  - Set `details=None`.
  - Include request id when available.

- `app/core/exceptions.py:93-112`
  - Replace raw/sanitized Pydantic error output with canonical validation details:

```json
[
  {
    "field": "client.full_name",
    "message": "...",
    "type": "missing"
  }
]
```

  - Strip leading FastAPI location prefixes: `body`, `query`, `path`, `header`, `cookie`.
  - Do not include raw `ctx`.
  - Use message: `חלק מהשדות אינם תקינים`.

- `app/core/exceptions.py:115-122`
  - Keep `set_request_error(exc, error_type="database_error")`.
  - Return safe Hebrew message only.
  - Do not leak SQLAlchemy internals.
  - Public response code must be `internal_server_error`, not `database_error`.
  - Public response message should be `אירעה שגיאה לא צפויה`.
  - Keep `database_error` only in logs/request summary via `set_request_error`.

- `app/core/exceptions.py:125-132`
  - Keep `set_request_error`.
  - Change error type/code to `internal_server_error`.
  - Return safe Hebrew message only.

- `app/core/exceptions.py:135-138`
  - Return `AppError` as:

```json
{
  "error": {
    "code": exc.code,
    "message": exc.message,
    "details": exc.details,
    "request_id": "..."
  }
}
```

- `app/core/exceptions.py:141-147`
  - Keep a `ValueError` handler.
  - Return status 400.
  - Use Hebrew message from the exception only if it is Hebrew.
  - Otherwise return `הבקשה אינה תקינה`.
  - Use public code `bad_request`.
  - Reserve `validation_error` for FastAPI/Pydantic `RequestValidationError`.

- `app/core/exceptions.py:150-162`
  - Keep one registration function: `setup_exception_handlers(app)`.
  - Register exactly:
    - `StarletteHTTPException`
    - `RequestValidationError`
    - `SQLAlchemyError`
    - `AppError`
    - `ValueError`
    - `Exception`

Add helpers in this file unless a cleaner existing local module already exists:
- `REQUEST_LOC_PREFIXES`
- `error_response`
- `validation_error_details`
- `_field_path`
- `_request_id`
- `contains_hebrew`
- `http_error_code_for_status`
- `http_error_message_for_status`

HTTP status mapping should be explicit and stable:
- `400`: `bad_request` / `הבקשה אינה תקינה`
- `401`: `unauthorized` / `נדרש אימות`
- `403`: `forbidden` / `אין הרשאה לביצוע הפעולה`
- `404`: `not_found` / `המשאב לא נמצא`
- `405`: `method_not_allowed` / `שיטת הבקשה אינה נתמכת`
- `409`: `conflict` / `הבקשה מתנגשת עם מצב קיים`
- `422`: `validation_error` / `חלק מהשדות אינם תקינים`
- `429`: `rate_limited` / `בוצעו יותר מדי בקשות`
- `500`: `internal_server_error` / `אירעה שגיאה לא צפויה`
- fallback `4xx`: `request_error` / `הבקשה אינה תקינה`
- fallback `5xx`: `internal_server_error` / `אירעה שגיאה לא צפויה`

### `app/core/logging_config.py`

Locations:
- `app/core/logging_config.py:496-503`
  - Existing functions: `set_request_id`, `clear_request_id`.
  - Add `get_request_id() -> str | None`.
  - It should return `request_id_ctx.get()`.

Do not create a second request id storage mechanism.

Do not create a new `app.core.logging_context` module. This project already stores request context in `app.core.logging_config`.

Do not replace `app/core/logging_config.py` with a simpler JSON formatter from another project. The current module also tracks request summaries, DB query counts, actor context, idempotency context, and error metadata. The only required logging change for this migration is adding `get_request_id()`.

### `app/middleware/request_id.py`

Locations:
- `app/middleware/request_id.py:62`
  - Current code reads or creates request id.
  - Add `request.state.request_id = request_id`.

- `app/middleware/request_id.py:77`
  - Keep `X-Request-ID` response header.

### `app/main.py`

Locations:
- `app/main.py:9`
- `app/main.py:51`

Expected action:
- Keep import and registration through `setup_exception_handlers(app)`.
- Do not register duplicate handlers elsewhere.

## Backend HTTPException Producers To Review

These places raise `HTTPException` directly and will flow through the new HTTP handler.
They do not necessarily need refactoring, but confirm their `detail` values remain valid Hebrew messages or structured details are intentionally replaced.

- `app/signature_requests/api/routes_advisor.py:83`
- `app/reports/services/reports_export_service.py:38`
- `app/reports/services/reports_export_service.py:43`
- `app/infrastructure/idempotency/dependency.py:50`
- `app/infrastructure/idempotency/dependency.py:55`
- `app/infrastructure/idempotency/dependency.py:60`
- `app/infrastructure/idempotency/dependency.py:97`
- `app/binders/api/binders_history.py:22`
- `app/reminders/api/routes_get.py:21`
- `app/users/api/deps.py:27`
- `app/users/api/deps.py:35`
- `app/users/api/deps.py:44`
- `app/users/api/deps.py:53`
- `app/users/api/deps.py:59`
- `app/users/api/deps.py:75`
- `app/users/api/auth.py:26`
- `app/tax_calendar/api/settings.py:19`
- `app/clients/api/clients.py:85`
- `app/clients/api/clients_excel.py:39`
- `app/clients/api/clients_excel.py:58`
- `app/clients/api/clients_excel.py:99`

Special note:
- `app/clients/api/clients.py:85` currently raises `HTTPException(..., detail=exc.detail)`.
- `exc.detail` is a dict from `ClientCreationConflictError`.
- That dict is built at `app/clients/services/create_client_service.py:277`.
- It currently contains `error`, `detail`, and `conflict`.
- This should be converted to `AppError(..., details={"conflict": conflict_payload})` or another clean service-level domain error.
- Do not preserve the old dict under `detail`.
- Do not pass the old dict as `details=old_detail_dict`.
- Normalize it, for example:

```python
raise AppError(
    message="לקוח עם פרטים אלה כבר קיים",
    code="CLIENT.CONFLICT",
    status_code=409,
    details={"conflict": conflict_payload},
)
```

- For deleted-client conflict, preserve the existing semantic code (`CLIENT.DELETED_EXISTS`) and status code, but still use a clean `details={"conflict": ...}` structure.

## External Core Snippets Not To Copy Blindly

The implementation may be informed by similar code from another project, but do not copy its module structure or providers directly.

Do not copy these patterns into this project:
- `from app.core.config import settings`
  - This project uses `from app.config import settings`.
- `from app.core.logging_context import get_request_id`
  - This project has request context in `app.core.logging_config`; add `get_request_id()` there.
- A separate `logging_context.py` with token-based `set_request_id/reset_request_id`
  - The current middleware and DB cleanup use `set_request_id` / `clear_request_id`; keep that lifecycle.
- A replacement `JsonFormatter` / `configure_logging`
  - The current `StructuredFormatter` and request summary machinery are richer and should stay.
- Brevo password-reset email code
  - This project currently uses SendGrid through `app/infrastructure/notifications.py` and has no Brevo settings. Email provider changes are unrelated to the error contract migration.
- Sentry setup
  - This project currently has no Sentry integration or settings. Do not add Sentry as part of this task.
- SlowAPI/rate limiter setup
  - This project currently has no SlowAPI dependency or rate limiter. Do not add one as part of this task.

If a rate-limit handler is added in a future task, it must use the canonical error envelope and the chosen `429` code from this audit (`rate_limited`) unless the project first standardizes a different name everywhere.

Do not copy the other project's keyword-only `AppError(code=..., message=...)` constructor. This project has many existing service calls in the form `AppError(message, code, status_code=...)`. Add `details` without forcing unrelated service-layer churn.


## Backend Tests That Must Change

Focused contract tests:
- `tests/core/api/test_error_handling.py:13-16`
  - Remove assertions for `error_meta`.
  - Assert `error` is an object.
  - Assert no top-level `detail`.
  - Assert no `error_meta`.
  - Assert `error.code`, `error.message`, `error.details`, and optional `error.request_id`.

API tests expecting top-level `error` string:
- `tests/correspondence/api/test_correspondence.py:78`
- `tests/correspondence/api/test_correspondence.py:99`
- `tests/signature_requests/api/test_signature_requests.py:181`
- `tests/businesses/api/test_business_binders_api.py:74`
- `tests/authority_contact/api/test_authority_contact.py:67`
- `tests/charge/api/test_charges_api_lifecycle.py:68`
- `tests/charge/api/test_charges_api_lifecycle.py:76`
- `tests/charge/api/test_charges_api_lifecycle.py:89`
- `tests/charge/api/test_charges_api_lifecycle.py:96`
- `tests/vat_reports/api/test_vat_reports_intake.py:16`
- `tests/vat_reports/api/test_vat_reports_intake.py:37`
- `tests/vat_reports/api/test_vat_reports_invoices_update_and_filters.py:120`
- `tests/vat_reports/api/test_vat_reports_materials_complete.py:38`
- `tests/annual_reports/api/test_annual_report_schedule.py:49`
- `tests/advance_payments/api/test_advance_payments_delete.py:58`
- `tests/annual_reports/api/test_annual_report_detail.py:81`
- `tests/annual_reports/api/test_annual_report_detail.py:89`
- `tests/annual_reports/api/test_annual_report_fixes.py:25`
- `tests/annual_reports/api/test_annual_report_annex.py:76`
- `tests/clients/api/test_clients_mutations_additional.py:71`
- `tests/users/api/test_user_management.py:137`

Replacement pattern:

```python
assert response.json()["error"] == "SOME.CODE"
```

becomes:

```python
payload = response.json()
assert payload["error"]["code"] == "SOME.CODE"
```

API tests expecting top-level `detail` string:
- `tests/signature_requests/api/test_signature_requests_cancel_and_client_list.py:103`
- `tests/infrastructure/test_idempotency.py:56`
- `tests/infrastructure/test_idempotency.py:93`
- `tests/clients/api/test_clients_excel.py:236`
- `tests/users/api/test_auth_deps.py:13`
- `tests/users/api/test_auth_deps.py:22`
- `tests/users/api/test_auth_deps.py:42`
- `tests/users/api/test_auth_deps.py:63`

Replacement pattern:

```python
assert response.json()["detail"] == "..."
```

becomes:

```python
assert response.json()["error"]["message"] == "..."
```

API tests expecting validation errors in top-level `detail` list:
- `tests/clients/api/test_clients_mutations_additional.py:290`
- `tests/clients/api/test_clients_mutations_additional.py:326`
- `tests/clients/api/test_clients.py:189`

Replacement pattern:

```python
errors = response.json()["detail"]
```

becomes:

```python
errors = response.json()["error"]["details"]
```

Then assert the new detail objects use:
- `field`
- `message`
- `type`

API tests expecting `error_meta`:
- `tests/core/api/test_error_handling.py:13-16`
- `tests/advance_payments/api/test_advance_payments.py:142`
- `tests/advance_payments/api/test_advance_payments.py:143`
- `tests/advance_payments/api/test_advance_payments.py:155`
- `tests/advance_payments/api/test_advance_payments_create_overview.py:67`
- `tests/advance_payments/api/test_advance_payments_create_overview.py:68`

Replacement:
- `error_meta.status_code` should be replaced by `response.status_code`.
- `error_meta.detail` should be replaced by `response.json()["error"]["message"]`.

Client creation conflict tests:
- `tests/clients/api/test_onboarding_layer1.py:74`
- `tests/clients/api/test_clients_mutations_additional.py:86`
- `tests/clients/api/test_clients_mutations_additional.py:123`

Current expectation reads a dict from `response.json()["detail"]`.
New expectation should read:

```python
payload = response.json()["error"]
assert payload["code"] in {"CLIENT.CONFLICT", "CLIENT.DELETED_EXISTS"}
assert payload["details"]["conflict"] is not None
```

Service tests:
- Most service tests that use `pytest.raises(AppError | NotFoundError | ConflictError)` should not need changes unless constructors are changed incompatibly.
- Keep `exc.value.code`, `exc.value.message`, and `str(exc.value)` behavior stable.

## Backend Documentation Mentions To Update

These READMEs mention `error_meta` and should be updated after the implementation:

- `app/correspondence/README.md:113`
- `app/invoice/README.md:59`
- `app/permanent_documents/README.md:161`
- `app/timeline/README.md:122`
- `app/reports/README.md:104`
- `app/infrastructure/README.md:67`
- `app/signature_requests/README.md:152`
- `app/dashboard/README.md:79`
- `app/businesses/README.md:174`
- `app/authority_contact/README.md:112`
- `app/charge/README.md:173`
- `app/binders/README.md:319`
- `app/users/README.md:139`

## Frontend Consumers To Update

Frontend repository:
- `../frontend`

### `../frontend/src/utils/utils.ts`

Locations:
- `../frontend/src/utils/utils.ts:149-167`
  - Current `getAxiosDetailMessage` parses legacy `detail` shapes.
  - Replace with a parser for the canonical backend contract.

- `../frontend/src/utils/utils.ts:184`
  - Currently reads `error.response?.data?.detail`.
  - Replace with `error.response?.data?.error?.message`.

- `../frontend/src/utils/utils.ts:187-190`
  - Remove `error_meta.detail` parsing completely.

Suggested behavior:
- Preserve timeout/network special cases.
- For backend API errors, return `data.error.message` when present.
- Do not parse legacy `detail` or `error_meta`.
- Optionally expose a typed helper for `data.error.code` and `data.error.details` if needed by callers.

### `../frontend/src/features/clients/utils/clientErrors.ts`

Location:
- `../frontend/src/features/clients/utils/clientErrors.ts:5`

Current code:

```ts
return err.response?.data?.error ?? err.response?.data?.code ?? err.response?.data?.detail?.error ?? null
```

Replace with:

```ts
return err.response?.data?.error?.code ?? null
```

Do not keep fallbacks to old backend shapes.

### `../frontend/src/features/annualReports/components/financials/financialHelpers.ts`

Location:
- `../frontend/src/features/annualReports/components/financials/financialHelpers.ts:133`

Current local parser reads `response.data.detail`.
Replace with canonical message reading or use the central frontend error helper.

### `../frontend/src/features/annualReports/components/tax/TaxCalculationPanel.tsx`

Location:
- `../frontend/src/features/annualReports/components/tax/TaxCalculationPanel.tsx:83`

Current local parser reads `response.data.detail`.
Replace with canonical message reading or use the central frontend error helper.

## Frontend Search Commands For Implementation Pass

Run from backend repo:

```bash
rg -n "error_meta|response\\.data\\?\\.detail|response\\.data\\.detail|data\\?\\.detail|data\\.detail|detail\\?\\.error|data\\.error|response\\.data\\.error" ../frontend/src -g '!node_modules'
```

Only true backend-error parsing matches should be changed. Do not touch unrelated UI props named `error`.

## Contract Tests To Add

Add or update tests under:
- `tests/core/api/test_error_handling.py`

Required assertions:
- Response has exactly top-level key `error` for errors.
- `error` is an object.
- `error.code` exists.
- `error.message` exists.
- `error.details` exists, even when `None`.
- `error.request_id` appears when `X-Request-ID` was provided.
- Response header `X-Request-ID` remains present.
- No top-level `detail`.
- No `error_meta`.
- No top-level string `error`.
- Validation details are normalized to `field`, `message`, `type`.
- Internal and database errors do not leak tracebacks, file paths, `.py`, SQL, or exception internals.
- `AppError.details` is returned when provided.

## Verification Commands

Backend minimum:

```bash
JWT_SECRET=test-secret pytest -q tests/core/api/test_error_handling.py
```

Backend targeted after replacing tests:

```bash
JWT_SECRET=test-secret pytest -q \
  tests/core/api/test_error_handling.py \
  tests/infrastructure/test_idempotency.py \
  tests/users/api/test_auth_deps.py \
  tests/clients/api/test_clients.py \
  tests/clients/api/test_clients_mutations_additional.py \
  tests/clients/api/test_onboarding_layer1.py
```

Frontend:
- Check `../frontend/package.json` for the existing typecheck/build/test commands.
- Run the smallest relevant frontend verification after updating frontend error parsing.

## Post-Implementation Cleanup Search

After implementation, these commands should return no legacy contract usage except intentional documentation of migration history:

```bash
rg -n "ErrorResponse|_error_json|error_meta|json\\(\\)\\[\\\"detail\\\"\\]|json\\(\\)\\['detail'\\]" app tests
rg -n "response\\.json\\(\\)\\[\\\"error\\\"\\]\\s*==|response\\.json\\(\\)\\['error'\\]\\s*==" tests
rg -n "error_meta|response\\.data\\?\\.detail|response\\.data\\.detail|data\\?\\.detail|data\\.detail|detail\\?\\.error" ../frontend/src -g '!node_modules'
```

Expected remaining backend assertions should use:

```python
response.json()["error"]["code"]
response.json()["error"]["message"]
response.json()["error"]["details"]
```
