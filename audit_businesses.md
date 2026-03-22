# Audit Report: `app/businesses/` Domain

**Date:** 2026-03-22
**Branch:** main
**Scope:** `app/businesses/` only — models, repositories, schemas, services, API

---

## 1. Model ↔ Schema ↔ Repo ↔ Service ↔ API Sync

**`app/businesses/schemas/business_schemas.py:39–52`** — `BusinessResponse` omits model fields `assigned_to`, `tax_id_number`, `phone`, `email` (business-level contact), `updated_at`. `assigned_to` is indexed in the model (`ix_business_assigned`) but absent from every schema. `tax_id_number` has a unique index but is never exposed. Business-level `phone`/`email` are stored but not surfaced.
Fix: add `assigned_to`, `tax_id_number`, `phone`, `email`, `updated_at` to `BusinessResponse`.
🟡

**`app/businesses/schemas/business_schemas.py:23–30`** — `BusinessUpdateRequest` has no `assigned_to`, `tax_id_number`, `phone`, `email` fields. Stored model fields cannot be updated through the API.
Fix: add these fields to `BusinessUpdateRequest` as `Optional`.
🟡

**`app/businesses/schemas/business_schemas.py:12–21`** — `BusinessCreateRequest` accepts no `assigned_to`, `tax_id_number`, `phone`, `email`, forcing a second PATCH call after creation.
Fix: add these fields as optional to `BusinessCreateRequest`.
🔵

**`app/businesses/repositories/business_repository.py:19–40`** — `create()` does not accept `tax_id_number`, `assigned_to`, `phone`, or `email`, so even if schemas include them, they can never be persisted at creation.
Fix: extend `create()` signature to include these keyword args.
🟡

**`app/businesses/__init__.py:1–3`** — exports `BusinessTaxProfile` but not `VatType`. Consumers cannot reach `VatType` via the package root.
Fix: add `VatType` to `__init__.py` exports.
🔵

---

## 2. Layer Separation

**`app/businesses/api/business_binders_router.py:34–38`** — direct `BusinessRepository(db).get_by_id(business_id)` call inside the API handler. Violates strict `API → Service → Repository` rule. The 404 raise also uses raw `HTTPException` instead of `NotFoundError`.
Fix: move lookup to a service method; replace `HTTPException` with `NotFoundError`.
🔴

**`app/businesses/api/business_binders_router.py:48–51`** — `service.enrich_binder(b)` called inside a list comprehension in the router. Enrichment is a service-layer concern; the router should receive fully formed objects.
Fix: move the comprehension into the service method and return enriched items.
🟡

**`app/businesses/api/business_tax_profile_router.py:22–25`** — `if profile is None: return BusinessTaxProfileResponse(business_id=business_id)` fallback is in the router. Deciding what to return when a profile is absent is business logic.
Fix: move the None-fallback to `BusinessTaxProfileService.get_profile()`.
🟡

**`app/businesses/repositories/business_tax_profile_repository.py:9`** — `BusinessTaxProfileRepository` inherits from `object`, not `BaseRepository`. All other repositories extend `BaseRepository`.
Fix: change to `class BusinessTaxProfileRepository(BaseRepository[BusinessTaxProfile])`.
🟡

**`app/businesses/services/business_service.py:160–168`** — manual `BusinessStatus(fields["status"])` conversion in the service after the schema already enforces the enum type. The double-validation adds noise.
Fix: remove the re-normalization; rely on the schema's enum enforcement.
🔵

**`app/businesses/services/business_tax_profile_service.py:25–33`** — manual `VatType(fields["vat_type"])` guard in service after schema has already enforced the enum. Same pattern as above.
Fix: remove redundant re-validation.
🔵

---

## 3. Duplicate Code

**`app/businesses/services/business_lookup.py:8–13`** and **`app/businesses/services/business_service.py:75–79`** — `get_business_or_raise` is implemented identically in two places: same error code `"BUSINESS.NOT_FOUND"`, same Hebrew message. `business_lookup.py` was presumably extracted as a shared utility but `BusinessService` duplicates it rather than delegating.
Fix: remove the copy in `business_service.py`; have the service call `get_business_or_raise` from `business_lookup.py`.
🔴

**`app/businesses/services/business_tax_profile_service.py:18–19` and `:23–24`** — both `get_profile` and `update_profile` independently call `self.business_repo.get_by_id(business_id)` and raise the same `NotFoundError`. Duplicate guard logic within the same file.
Fix: extract `_assert_business_exists(business_id)` private method.
🔵

**`app/businesses/repositories/business_repository.py:82–155`** — `list()` and `count()` build identical `join + filter` chains for `status`, `business_type`, and `search` (40+ lines each). Any filter change must be applied in both places.
Fix: extract `_build_base_query(status, business_type, search)` private method used by both.
🟡

---

## 4. File Naming

**`app/businesses/api/businesses.py`** — defines two distinct routers (`client_businesses_router` and `businesses_router`). Neither is registered in `router_registry.py` (see finding 8.1). After registering, consider splitting into:
- `businesses.py` — standalone `/businesses` CRUD
- `client_businesses_router.py` — nested `/clients/{client_id}/businesses`
🔵

**`app/businesses/services/status_card_service.py`** — filename lacks the `business_` prefix used by every other file in the `services/` directory.
Fix: rename to `business_status_card_service.py`.
🔵

**`app/businesses/services/business_lookup.py`** — 14-line single-function file. Given that `BusinessService` duplicates it (finding 3.1), its purpose is undermined. Either consolidate into `business_guards.py` or ensure `BusinessService` delegates to it.
🔵

---

## 5. Global Extraction Candidates

**`app/businesses/models/business.py:11–22`** — `BusinessType` and `BusinessStatus` mirror `ClientType` / `ClientStatus` values in the `clients` domain (`OSEK_PATUR`, `OSEK_MURSHE`, `COMPANY`, `EMPLOYEE` / `ACTIVE`, `FROZEN`, `CLOSED`). These are shared Israeli legal entity classifications.
Fix (long-term): centralize in `app/common/` or `app/core/enums.py` to prevent value drift.
🔵

**`app/businesses/models/business_tax_profile.py:10–13`** — `VatType` is defined here but may also be used or redefined in the `vat_reports` domain. If so, it should live in `app/common/`.
Fix (long-term): verify usage in `vat_reports`; move to `app/common/` if used by 2+ domains.
🔵

---

## 6. Constants

**`app/businesses/services/business_service.py:14`** — `_HAS_SIGNALS_FETCH_LIMIT = 1000` is a documented architectural debt limit defined inline at module level. The project convention is to document such limits in `CLAUDE.md` (already done) and name them explicitly.
Fix: move to `app/businesses/constants.py` (create if needed); cross-reference in `CLAUDE.md`.
🟡

**`app/businesses/services/status_card_service.py:103` and `:113`** — `page_size=10_000` used to simulate "fetch all" for charges and advance payments. Unnamed magic constant representing an architectural debt ceiling.
Fix: extract as `_STATUS_CARD_CHARGE_FETCH_LIMIT = 10_000` in `constants.py`; document in `CLAUDE.md`.
🟡

**`app/businesses/api/business_status_card_router.py:22`** — `ge=2000, le=2100` year range inline. Will likely appear on other status-card endpoints.
Fix: extract as `MIN_FISCAL_YEAR = 2000` / `MAX_FISCAL_YEAR = 2100` shared constant.
🔵

---

## 7. File Size

**`app/businesses/services/business_service.py`** — **267 lines**, 117 over the 150-line hard limit.
Fix: split into:
- `business_service.py` (~130 lines): Create, Read, Update, Delete, Restore
- `business_bulk_service.py` (~50 lines): `bulk_update_status` + `_business_has_operational_signals`
🔴

**`app/businesses/api/businesses.py`** — **224 lines**, 74 over the limit. Also defines two distinct routers.
Fix: split into:
- `businesses.py` — standalone `/businesses` router (CRUD + bulk)
- `client_businesses_router.py` — nested `/clients/{client_id}/businesses` router
🔴

**`app/businesses/repositories/business_repository.py`** — **215 lines**, 65 over the limit. Deduplication of `list()`/`count()` (finding 3.3) removes ~35 lines. If still over after that, move `list_all`, `list_by_ids`, `list_by_client*` to `business_repository_read.py`.
🔴

---

## 8. Completeness

**`app/router_registry.py:18`** — `businesses.py` defines `client_businesses_router` and `businesses_router` but neither is imported or registered. All 8 business CRUD endpoints are **completely unreachable**:
- `POST /clients/{client_id}/businesses`
- `GET /clients/{client_id}/businesses`
- `GET /businesses`
- `GET /businesses/{business_id}`
- `PATCH /businesses/{business_id}`
- `DELETE /businesses/{business_id}`
- `POST /businesses/{business_id}/restore`
- `POST /businesses/bulk-action`

Fix: add `client_businesses_router, businesses_router` to the import at line 18 and register both routers.
🔴

**`app/businesses/api/businesses.py:202–223`** — `POST /businesses/bulk-action` is a bulk write operation with no idempotency key. Per project rule: *"Sensitive write operations (imports, bulk actions, background triggers) must require an idempotency key."*
Fix: add `Idempotency-Key` header or body field to the bulk action endpoint.
🔴

**`app/businesses/services/business_service.py:155–156`** — `update_business` returns `None` when the business is not found. The router at `businesses.py:162–165` then raises a raw `HTTPException` instead of the project-standard `NotFoundError`, breaking the centralized error envelope.
Fix: have `update_business` raise `NotFoundError` directly; remove raw `HTTPException` from router.
🔴

**`app/businesses/services/business_service.py:187–192`** and **`app/businesses/api/businesses.py:178–181`** — `delete_business` returns `False` on not-found; same raw `HTTPException` anti-pattern.
Fix: raise `NotFoundError` in service; remove raw `HTTPException` from router.
🔴

**`app/businesses/repositories/business_repository.py:73–80`** — `list_by_client_including_deleted` exists in the repo but is never called by any service or exposed by any endpoint. Restore endpoint exists but there is no way to discover what was deleted.
Fix: add `GET /clients/{client_id}/businesses?include_deleted=true` or a dedicated list-deleted endpoint.
🟡

**`app/businesses/models/business_tax_profile.py`** — no `deleted_at`/`deleted_by` columns. If the parent business is soft-deleted, the tax profile orphans with no lifecycle management.
Fix: add soft-delete columns to `BusinessTaxProfile`; cascade soft-delete from business.
🟡

**`app/businesses/services/status_card_service.py:118–122`** — `_binders_card` fetches binders by `client_id`, not `business_id`. If a client has multiple businesses, all status cards show the same binder total. The intent is architecturally correct (binders belong to clients) but is undocumented.
Fix: add an inline comment explaining why binder count is client-scoped.
🟡

---

## 9. Dead Code

**`app/businesses/services/business_lookup.py:8–13`** — `get_business_or_raise` is never called by `BusinessService` (which duplicates it). Verify no other domain calls it; if unused, it is dead code. See finding 3.1.
🟡

**`app/businesses/models/business.py:91–98`** — `contact_phone` / `contact_email` computed properties are referenced by no schema, no service, and no API response.
Fix: either surface in `BusinessResponse` or remove.
🔵

**`app/businesses/models/business.py:81–88`** — `full_name` property defined on the model but `BusinessResponse` uses `business_name` directly; `BusinessWithClientResponse` uses `business.client.full_name` directly. The property is unused.
Fix: either use in schemas or remove.
🔵

**`app/businesses/repositories/business_repository.py:73–80`** — `list_by_client_including_deleted` is never called. See finding 8.5.
🔵

**`app/businesses/repositories/business_repository.py:157–162`** — `list_all()` fetches all non-deleted businesses with no limit and is not called from any endpoint. Its purpose is unclear.
Fix: document purpose or remove.
🟡

---

## 10. Pagination

**`app/businesses/services/business_service.py:81–86`** and **`app/businesses/api/businesses.py:82–95`** — `GET /clients/{client_id}/businesses` returns `ClientBusinessesResponse` with a `total` but no `page`/`page_size`. The repo call (`list_by_client`) is unbounded. Per project rule: *"Every list endpoint must support standardized pagination."*
Fix: add `page: int = 1, page_size: int = 20` query params; update service and repo to use `_paginate()`.
🔴

**`app/businesses/services/status_card_service.py:103` and `:113`** — `page_size=10_000` simulates "fetch all" for charges and advance payments. This is undocumented architectural debt.
Fix: extract as a named constant; add to `CLAUDE.md` architectural debt table.
🟡

**`app/businesses/services/status_card_service.py:119` and `:125`** — `list_by_client` and `list_by_business` return all records with no limit. No ceiling documented.
Fix: document with named constants; add to `CLAUDE.md` architectural debt table.
🟡

---

## 11. Israeli Domain Logic

**`app/businesses/schemas/business_schemas.py`** — `tax_id_number` is absent from all request schemas (finding 1.1), so no ת.ז. / ח.פ. checksum validation is applied. Israeli t.z. (9-digit personal ID) uses a Luhn-style checksum; ח.פ. (company registration number) uses a modulo-10 algorithm.
Fix: add `tax_id_number` to create/update schemas with a validator that runs the appropriate checksum based on `business_type`.
🟡

**`app/businesses/models/business_tax_profile.py:32`** and **`app/businesses/schemas/business_tax_profile_schemas.py:28`** — `vat_exempt_ceiling` stores the OSEK PATUR exemption ceiling with no reference to the statutory value (₪120,000 for 2024, revised annually). No warning is raised when value deviates from the statutory threshold.
Fix: add a named constant for the current statutory ceiling; optionally warn in service if value is set significantly outside range.
🔵

**`app/businesses/services/business_tax_profile_service.py`** — no cross-validation that `VatType.EXEMPT` is only assigned to `OSEK_PATUR` businesses. Assigning `EXEMPT` to an `OSEK_MURSHE` or `COMPANY` is legally incorrect under Israeli tax law.
Fix: add guard in `update_profile()`: fetch business type and raise `AppError` if `vat_type=EXEMPT` and `business_type != OSEK_PATUR`.
🟡

**`app/businesses/schemas/business_tax_profile_schemas.py:30`** — `advance_rate` validated as `ge=0, le=100`. The realistic range for Israeli advance tax payments (מקדמות) is typically 0–40% of turnover. Values like 99% are nonsensical.
Fix: tighten to `le=40` or add a warning comment explaining the legal range.
🔵

**`app/businesses/models/business_tax_profile.py:36`** — `fiscal_year_start_month` accepts any month 1–12 with no validation against business type. Israeli companies generally must use a January fiscal year start or obtain specific approval.
Fix: document the business-type constraint; optionally validate in service.
🔵

**`app/businesses/schemas/business_schemas.py:18`** — `opened_at: date` has no `le=today` validation. Future business opening dates are nonsensical in a tax CRM.
Fix: add `@field_validator('opened_at') def opened_at_not_future(cls, v): assert v <= date.today(); return v`.
🟡

---

## 12. Response Consistency

**`app/businesses/schemas/business_status_card.py:17`** — `AnnualReportCard.filing_deadline: Optional[str]`. All other date fields in this codebase use `date` or `datetime` Pydantic types. The service manually formats this string at `status_card_service.py:88`. Using a raw string breaks ISO 8601 consistency.
Fix: change to `Optional[date]`; remove manual `.strftime()` in the service.
🟡

**`app/businesses/schemas/business_schemas.py:49`** — `BusinessResponse.created_at: Optional[datetime]`. The model column is `nullable=False` with a `default=func.now()`. It is never `None` in practice.
Fix: change to `created_at: datetime` (non-optional).
🟡

**`app/businesses/schemas/business_schemas.py:50`** — `available_actions: list[dict[str, Any]] = Field(default_factory=list)` uses untyped `dict`. If other domains use a typed `ActionItem` schema, this is a consistency gap.
Fix: define `ActionItem` schema in `app/actions/` and reference it here.
🔵

**`app/businesses/schemas/business_status_card.py:43`** — `BusinessStatusCardResponse` includes both `client_id` and `business_id`. This is intentional but undocumented — the endpoint is `/businesses/{id}/status-card` yet returns a `client_id`.
Fix: add a docstring or comment explaining why `client_id` is included.
🔵

---

## 13. Authorization Consistency

**`app/businesses/api/business_tax_profile_router.py:28–39`** — `PATCH /businesses/{business_id}/tax-profile` updates financial tax data (VAT type, advance rate, exempt ceiling) but is accessible to SECRETARY role via the router-level `require_role(ADVISOR, SECRETARY)`. Financial data writes should be ADVISOR-only.
Fix: add `dependencies=[Depends(require_role(UserRole.ADVISOR))]` to the PATCH endpoint.
🔴

**`app/businesses/api/businesses.py:144–166`** — `PATCH /businesses/{business_id}` inherits the router-level `require_role(ADVISOR, SECRETARY)` with no endpoint-level override. A SECRETARY can call PATCH and attempt to change `status` to CLOSED/FROZEN — the service blocks it internally (`user_role != UserRole.ADVISOR`), but per project rules auth checks belong at the API boundary.
Fix: either split into a separate status-change endpoint with ADVISOR-only or add endpoint-level role check for status-change path.
🟡

**`app/businesses/api/businesses.py:186–199`** and **`app/businesses/services/business_service.py:200–205`** — `restore_business` has ADVISOR check at both endpoint level (`dependencies=[Depends(require_role(UserRole.ADVISOR))]`) and service level. The redundancy is defensive and acceptable, but should be documented as intentional.
🔵

---

## 14. Soft Delete Consistency

**`app/businesses/repositories/business_repository.py:177–185`** — `soft_delete()` fetches the record with `self.db.query(Business).filter(Business.id == business_id).first()`, **bypassing** the `deleted_at.is_(None)` guard. Calling `soft_delete` on an already-deleted business silently overwrites `deleted_at` and `deleted_by`, destroying the original audit trail.
Fix: replace with `self.get_by_id(business_id)` (which already filters soft-deleted); return `False` cleanly if already deleted.
🔴

**`app/businesses/repositories/business_repository.py:193`** — `restore()` sets `business.deleted_by = None`, clearing who originally deleted it. `restored_by` already captures restoration provenance; the deletion `deleted_by` should be preserved for the full audit trail (important for Israeli bookkeeping compliance).
Fix: remove `business.deleted_by = None` from `restore()`.
🟡

**`app/businesses/models/business_tax_profile.py`** — `BusinessTaxProfile` has no soft-delete columns. If the parent business is soft-deleted, the profile is orphaned. See also finding 8.6.
🟡

---

## 15. Error Message Language

All `raise` statements in `app/businesses/` use Hebrew `message` strings. Full pass:

| File | Finding |
|---|---|
| `business_guards.py` | All messages Hebrew ✓ |
| `business_lookup.py` | Hebrew ✓ |
| `business_service.py` | All messages Hebrew ✓ |
| `business_tax_profile_service.py` | All messages Hebrew ✓ |
| `status_card_service.py` | Hebrew ✓ |
| `businesses.py:162–165, 178–181` | Messages Hebrew ✓, but uses raw `HTTPException` instead of `NotFoundError` — breaks error envelope format |
| `business_binders_router.py:36–38` | Hebrew ✓, but uses raw `HTTPException` (also has repo-in-API violation) |

**`app/businesses/api/businesses.py:162–165` and `:178–181`** — `raise HTTPException(status_code=404, detail="העסק לא נמצא")` bypasses `AppError` / centralized error handler. Message is Hebrew but response envelope structure differs from every other endpoint.
Fix: have the service raise `NotFoundError`; remove `HTTPException` from router.
🟡

**`app/businesses/api/business_binders_router.py:36–38`** — same `HTTPException` pattern; covered under finding 2.1 (blocking).
🔴

---

## Summary Table

| Category               | Status | Count (🔴/🟡/🔵) |
| ---------------------- | ------ | ----------------- |
| Model↔Schema sync      | ⚠️     | 0/3/2             |
| Layer separation       | ❌     | 1/3/2             |
| Duplicate code         | ❌     | 1/1/1             |
| File naming            | ⚠️     | 0/0/3             |
| Global extraction      | ✅     | 0/0/2             |
| Constants              | ⚠️     | 0/2/1             |
| File size              | ❌     | 3/0/0             |
| Completeness           | ❌     | 4/3/0             |
| Dead code              | ⚠️     | 0/2/3             |
| Pagination             | ❌     | 1/2/0             |
| Israeli domain logic   | ⚠️     | 0/3/3             |
| Response consistency   | ⚠️     | 0/2/2             |
| Authorization          | ❌     | 1/1/1             |
| Soft delete            | ❌     | 1/2/0             |
| Error message language | ⚠️     | 1/1/0             |
| **Total**              |        | **13 / 25 / 20**  |

---

## Blocking Issues — Priority Order

1. **Router registration** — register `client_businesses_router` + `businesses_router` in `router_registry.py`; entire CRUD domain is dead
2. **`business_service.py` 267 lines** — split required before next commit
3. **`businesses.py` 224 lines** — split required
4. **`business_repository.py` 215 lines** — split required
5. **Repo call in API** — `business_binders_router.py:34` direct repo access; move to service
6. **`PATCH /tax-profile` SECRETARY access** — restrict to ADVISOR
7. **`soft_delete()` overwrites audit trail** — use `get_by_id()` in repo
8. **`update_business` / `delete_business` return falsy** — raise `NotFoundError` in service
9. **`GET /clients/{id}/businesses` no pagination** — add `page` / `page_size`
10. **Bulk action missing idempotency key** — add per project rule
11. **`get_business_or_raise` duplicated** — consolidate to `business_lookup.py`
12. **Raw `HTTPException` in routers** — replace with domain error classes
