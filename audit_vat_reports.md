# Domain Audit: `vat_reports`

Audit date: 2026-03-22

---

## 1. Model ↔ Schema ↔ Repo ↔ Service ↔ API Sync

**🟡 `vat_invoice_repository.py:29` — `invoice_date` typed as `datetime` in repo `create()`, but model column is `Date`**
`file: vat_invoice_repository.py:29` — `create()` signature declares `invoice_date: datetime` but the ORM column `VatInvoice.invoice_date` is `Column(Date)`. SQLAlchemy will coerce this silently but the type hint is wrong and will confuse callers.
Fix: change parameter type to `date`.

**🟡 `vat_invoice_repository.py:2` — unused `datetime` import**
`file: vat_invoice_repository.py:2` — `from datetime import datetime` is imported but `datetime` is only used in the type hint (which itself is wrong — see above).
Fix: change to `from datetime import date`, update type hint.

**🟡 `vat_client_summary_repository.py:43` — `get_periods_for_business` missing `deleted_at` filter**
`file: repositories/vat_client_summary_repository.py:43` — `VatWorkItem` query has no `deleted_at.is_(None)` filter. Soft-deleted work items will appear in the summary.
Fix: add `.filter(VatWorkItem.deleted_at.is_(None))`.

**🟡 `vat_client_summary_repository.py:20` — `get_annual_output_vat` missing `deleted_at` filter**
`file: repositories/vat_client_summary_repository.py:20` — Same issue as above on the `get_annual_output_vat` query.
Fix: add `.filter(VatWorkItem.deleted_at.is_(None))`.

**🟡 `vat_client_summary_repository.py:48` — `get_annual_aggregates` missing `deleted_at` filter**
`file: repositories/vat_client_summary_repository.py:64` — Same issue.
Fix: add `.filter(VatWorkItem.deleted_at.is_(None))`.

**🔵 `VatInvoiceResponse.created_at` typed `date` but model stores `utcnow` (a datetime)**
`file: schemas/vat_report.py:146` — `created_at: date` in `VatInvoiceResponse` while the model column is `Column(Date, default=utcnow)`. `utcnow` returns a `datetime`, not a `date`, so on SQLite the stored value may be a full datetime string. Pydantic will coerce it but the schema comment says "Date במודל" which is misleading.
Fix: keep as `date` but ensure `utcnow` in the model is replaced with `date.today` for the `created_at` default on `VatInvoice`.

**🟡 `VatWorkItemCreateRequest` missing `period_type` — repo `create()` requires it**
`file: repositories/vat_work_item_repository.py:22` — `create()` accepts `period_type` as a positional param (no default). The service `intake.create_work_item` calls `work_item_repo.create(...)` without passing `period_type` — this will raise `TypeError` at runtime.
`file: services/intake.py:82` — the call is `work_item_repo.create(business_id, period, created_by, status, ...)` with no `period_type`.
Fix: pass `period_type` (sourced from `profile.vat_type`) in `intake.create_work_item`.

---

## 2. Layer Separation

**🟡 `routes_queries.py:9` — API layer imports internal service helper directly**
`file: api/routes_queries.py:9` — `from app.vat_reports.services.vat_report_queries import _compute_deadline_fields` imports a private function (prefixed `_`) directly into the API layer, bypassing the service façade.
Fix: expose `compute_deadline_fields` (without `_`) through `VatReportService` or `vat_report_queries` public API.

**🟡 `routes_queries.py:21-31` — Business logic in API router**
`file: api/routes_queries.py:21` — `_serialize()` computes deadline fields and maps enrichment data inside the router. This is business/presentation logic that belongs in the service layer.
Fix: move `_serialize` into `vat_report_queries.py` and return fully-serialized dicts from the service.

**🟡 `routes_filing.py:32-36` — Manual role check instead of `require_role` dependency**
`file: api/routes_filing.py:32` — `if current_user.role != UserRole.ADVISOR: raise HTTPException(...)` is a manual role check. Project convention is to use `require_role()` as a FastAPI dependency.
Fix: replace with `current_user: Annotated[User, Depends(require_role(UserRole.ADVISOR))]`.

**🟡 `data_entry_invoice_update.py:48` — Service creates a new repository directly**
`file: services/data_entry_invoice_update.py:48` — `BusinessRepository(work_item_repo.db)` instantiated inside a service helper. Same pattern exists in `data_entry_invoices.py:59`. Repo should be injected, not constructed ad hoc.
Fix: pass `business_repo` as a parameter (already done in `VatReportService.__init__`; thread it through `data_entry.update_invoice` call).

---

## 3. Duplicate Code

**🟡 `data_entry_invoices.py` and `data_entry_invoice_update.py` both instantiate `BusinessRepository` inline**
Files: `services/data_entry_invoices.py:59`, `services/data_entry_invoice_update.py:48` — identical pattern: `BusinessRepository(work_item_repo.db).get_by_id(item.business_id)`.
Fix: pass `business_repo` from the façade in both calls.

**🟡 `recalculate_totals` in `data_entry_common.py` only updates VAT fields, not net totals**
`file: services/data_entry_common.py:36-37` — `update_vat_totals` signature accepts `total_output_net` / `total_input_net` but `recalculate_totals()` calls it with only `output_vat, input_vat` — missing the net fields.
`file: repositories/vat_work_item_repository.py:190` — `update_vat_totals` has required params `total_output_net` and `total_input_net` with no defaults. The call in `data_entry_common.py:37` `work_item_repo.update_vat_totals(item_id, output_vat, input_vat)` will raise `TypeError` at runtime (missing 2 required positional arguments).
Fix: `recalculate_totals` must also sum net amounts from invoices and pass them through.

---

## 4. File Naming

**🔵 `vat_client_summary_schema.py` naming inconsistency**
`file: schemas/vat_client_summary_schema.py` — All other schema files are named `vat_*.py` without the `_schema` suffix (e.g. `vat_report.py`, `vat_audit.py`). This file has a `_schema` suffix.
Fix: rename to `vat_client_summary.py` and update imports.

**🔵 `vat_client_summary_repository.py` — exported class not listed in `repositories/__init__.py`**
`file: repositories/__init__.py` — exports only `VatInvoiceRepository`, `VatWorkItemRepository`. `VatClientSummaryRepository` is not exported.
Fix: add `VatClientSummaryRepository` to `__init__.py`.

---

## 5. Global Extraction

**🔵 `SubmissionMethod` imported from `annual_reports` domain in 3 vat_reports files**
Files: `models/vat_work_item.py:28`, `repositories/vat_work_item_repository.py:12`, `services/filing.py:10`, `schemas/vat_report.py:20` — `SubmissionMethod` is shared with `annual_reports`. Cross-domain model import at the model/repo level violates project rules.
Fix: move `SubmissionMethod` to `app/common/` or `app/core/enums.py` and import from there in both domains.

---

## 6. Constants

**🟡 `constants.py:48` — `CATEGORY_LABELS_SERVER` is missing several categories present in `CATEGORY_DEDUCTION_RATES`**
`file: services/constants.py:36-48` — `CATEGORY_LABELS_SERVER` has 11 entries; `CATEGORY_DEDUCTION_RATES` has 22 entries. Categories like `fuel`, `vehicle_maintenance`, `vehicle_leasing`, `maintenance`, `utilities`, `communication`, `postage_and_shipping`, `bank_fees`, `tolls_and_parking`, `mixed_expense`, `vehicle_insurance`, `insurance`, `municipal_tax` have no label. The auto-fill in `data_entry_invoices.py:81` falls back to `"לא ידוע"` for these.
Fix: add missing Hebrew labels for all categories in `CATEGORY_LABELS_SERVER`.

**🔵 `page_size` default is 50 in routes and repos, but project standard is 20**
`file: api/routes_queries.py:65` — `page_size: int = Query(default=50, ...)` and `repositories/vat_work_item_repository.py:78` — `page_size: int = 50`. Project rule: default `page_size=20`.
Fix: change default to 20 in both places.

---

## 7. File Size

**🟡 `vat_work_item_repository.py` — 273 lines (exceeds 150-line limit)**
`file: repositories/vat_work_item_repository.py` — 273 lines.
Fix: split audit log methods (`append_audit`, `get_audit_trail`) into a separate `VatAuditLogRepository`.

**🟡 `vat_report_queries.py` — 184 lines (exceeds 150-line limit)**
`file: services/vat_report_queries.py` — 184 lines.
Fix: split enrichment helpers (`get_work_item_enriched`, `get_business_items_enriched`, `get_list_enriched`, `get_audit_trail_enriched`) into `vat_report_enrichment.py`.

**🟡 `schemas/vat_report.py` — 169 lines (exceeds 150-line limit)**
`file: schemas/vat_report.py` — 169 lines.
Fix: split invoice schemas (`VatInvoiceCreateRequest`, `VatInvoiceResponse`, `VatInvoiceListResponse`, `VatInvoiceUpdateRequest`) into `vat_invoice_schema.py`.

---

## 8. Completeness

**🔴 `intake.create_work_item` does not pass `period_type` to `work_item_repo.create()`**
`file: services/intake.py:82` — `work_item_repo.create()` requires `period_type` but it is never passed. `create()` has no default for this param. This will raise `TypeError` on every work item creation.
Fix: source `period_type` from `profile.vat_type` and pass it to `work_item_repo.create(period_type=profile.vat_type if profile else VatType.MONTHLY)`.

**🔴 `recalculate_totals` call is missing `total_output_net` / `total_input_net` arguments**
`file: services/data_entry_common.py:37` — `work_item_repo.update_vat_totals(item_id, output_vat, input_vat)` is missing the required `total_output_net` and `total_input_net` positional arguments. This will raise `TypeError` on every invoice mutation.
Fix: sum net amounts in `recalculate_totals` using `invoice_repo` and pass all four values.

**🟡 `VatInvoiceListResponse` has no `total` field — invoice list endpoint is unbounded**
`file: schemas/vat_report.py:151` and `api/routes_data_entry.py:51-63` — invoice list endpoint returns all invoices for a work item with no pagination. For large work items this is unbounded. The response schema also has no `total` count.
Fix: add pagination to invoice list endpoint or at minimum add a `total` field.

**🟡 No endpoint to delete / soft-delete a work item**
`file: api/` — there is no DELETE endpoint for `VatWorkItem`. Once created with wrong business/period there is no way to remove it from the UI.
Fix: add `DELETE /vat/work-items/{item_id}` (ADVISOR only, soft-delete, blocked if FILED).

**🟡 `list_by_business` is unbounded**
`file: repositories/vat_work_item_repository.py:63` — `list_by_business` fetches all work items for a business with no pagination or limit.
Fix: add pagination or at least a reasonable `limit` for safety.

---

## 9. Dead Code

**🟡 `vat_invoice_repository.py:17` — duplicate import of `VatRateType`**
`file: repositories/vat_invoice_repository.py:11,17` — `VatRateType` is imported twice: once in the multi-import block (line 11) and again on line 17.
Fix: remove the duplicate `from app.vat_reports.models.vat_enums import VatRateType` on line 17.

**🟡 `data_entry_common.py:5` — `Tuple` imported but not used as annotation at runtime**
`file: services/data_entry_common.py:5` — `from typing import Tuple` is imported; function `recalculate_totals` uses `Tuple[float, float]` as return annotation but this is Python 3.9+, where `tuple[float, float]` is preferred and `Tuple` from `typing` is deprecated.
Fix: replace `Tuple` with the built-in `tuple`.

**🔵 `MarkMaterialsCompleteRequest` schema is empty**
`file: schemas/vat_report.py:84` — `MarkMaterialsCompleteRequest(BaseModel): pass` exists but is never used (the route doesn't accept a body). It's imported nowhere.
Fix: delete the class.

---

## 10. Pagination

**🟡 `routes_queries.py:65` — `page_size` default is 50, not 20**
`file: api/routes_queries.py:65` — project standard default is `page_size=20`.
Fix: change to `page_size: int = Query(default=20, ge=1, le=200)`.

**🟡 `list_by_business` at `routes_queries.py:47` has no pagination**
`file: api/routes_queries.py:47-56` — `list_business_work_items` endpoint returns all items for a business with no `page`/`page_size` params, and `total=len(items)` which is always correct but the endpoint will degrade for large accounts.
Fix: add pagination params and use the paginated repo methods.

**🔵 Invoice list endpoint is unbounded (noted in §8 above)**

---

## 11. Israeli Domain Logic

**🟡 `vat_report.py:124` — counterparty ת"ז (IL_PERSONAL) validated only by length, no Luhn checksum**
`file: schemas/vat_report.py:123-125` — validation checks `len(cid) == 9 and cid.isdigit()` for both `IL_BUSINESS` (עוסק מורשה) and `IL_PERSONAL` (ת"ז). Israeli ID numbers require a Luhn-variant checksum validation.
Fix: add ת"ז checksum validator (standard Israeli algorithm).

**🟡 OSEK PATUR ceiling check in `data_entry_common.py` does not exclude canceled/credit invoices**
`file: services/data_entry_common.py:111` — `invoice_repo.sum_income_net_by_business_year` sums all INCOME invoices without filtering `CREDIT_NOTE` document types. Credit notes reduce actual turnover and should be excluded from the ceiling sum.
Fix: filter out `DocumentType.CREDIT_NOTE` in `sum_income_net_by_business_year`.

**🔵 `_validate_period_for_vat_type` only checks bimonthly even months; does not validate year range**
`file: services/intake.py:16-29` — bimonthly validation blocks even months but does not block periods more than a year in the future (speculative reporting) or before a business's registration date.
Fix: add reasonable future period guard (e.g. not more than 2 months ahead).

---

## 12. Response Consistency

**🟡 `VatWorkItemResponse.business_status` returns `Optional[BusinessStatus]` as raw enum value string**
`file: schemas/vat_report.py:44` — `business_status: Optional[BusinessStatus] = None`. The service sets it via `business.status.value` (a string), but the schema declares it as `Optional[BusinessStatus]`. This inconsistency may cause serialization confusion.
Fix: unify — either declare `business_status: Optional[str]` or set it as enum directly.

**🟡 `VatWorkItemResponse` missing `created_by_name`**
`file: schemas/vat_report.py:40-72` — `assigned_to_name` and `filed_by_name` are enriched but `created_by` (present) has no corresponding `created_by_name`. Inconsistent with enrichment pattern.
Fix: add `created_by_name: Optional[str]` and populate in enrichment helpers.

---

## 13. Authorization Consistency

**🔴 `routes_intake.py` — no `require_role` on `create_work_item` or `mark_materials_complete`**
`file: api/routes_intake.py:15-56` — both endpoints only use `CurrentUser` (authentication only). Docstrings say "Accessible by: receptionist, secretary, advisor" but no role check is enforced.
Fix: add `Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))` to both endpoints.

**🔴 `routes_queries.py` — no `require_role` on any query endpoint**
`file: api/routes_queries.py:34,47,59,82` — all four endpoints use only `CurrentUser`. Any authenticated user can access VAT data.
Fix: add `Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))` to all query endpoints.

**🔴 `routes_data_entry.py` — no `require_role` on invoice CRUD endpoints**
`file: api/routes_data_entry.py:20,50,66,97` — all four invoice endpoints use only `CurrentUser`.
Fix: add `require_role(UserRole.ADVISOR, UserRole.SECRETARY)` on add/update/list; restrict delete to `ADVISOR` only.

**🔴 `routes_status.py:15` — `mark_ready_for_review` has no `require_role`**
`file: api/routes_status.py:15` — uses only `CurrentUser`. The `send_back` endpoint correctly uses `require_role(UserRole.ADVISOR)` but `ready_for_review` has no role constraint.
Fix: add `require_role(UserRole.ADVISOR, UserRole.SECRETARY)`.

**🔴 `routes_filing.py:32` — manual `if role != ADVISOR` instead of dependency**
`file: api/routes_filing.py:32-36` — raises `HTTPException` manually rather than using the project-standard `require_role` dependency. This bypasses any future middleware that wraps `require_role`.
Fix: use `Annotated[User, Depends(require_role(UserRole.ADVISOR))]`.

---

## 14. Soft Delete Consistency

**🔴 `vat_client_summary_repository.py` — all three queries missing `deleted_at` filter (see §1)**
Soft-deleted work items appear in business summaries and annual aggregates.

**🟡 No soft-delete endpoint exists for `VatWorkItem`**
Service and repo support soft-delete fields (`deleted_at`, `deleted_by`) but there is no code path that ever sets them. The feature is wired but not callable.
Fix: implement soft-delete in service + add API endpoint (linked to §8 completeness).

**🟡 `VatInvoice` has no `deleted_at` column — invoices are hard-deleted**
`file: models/vat_invoice.py` — invoices are permanently deleted via `self.db.delete(invoice)`. The audit log captures the deletion, but the record is gone.
Fix: this is a design choice; if intentional, document it. If audit trail completeness is required, consider soft-delete + exclusion from active queries.

---

## 15. Error Message Language

**🟡 `data_entry_common.py:17` — English prefix in error message**
`file: services/data_entry_common.py:17` — `"filed: לא ניתן לערוך..."` — the `"filed:"` prefix is English and will surface to users.
Fix: remove the English prefix.

**🟡 `data_entry_common.py:68` — English prefix in error message**
`file: services/data_entry_common.py:68` — `"negative: הסכום של המע\"מ..."` — English prefix.
Fix: remove.

**🟡 `data_entry_common.py:70` — English prefix in error message**
`file: services/data_entry_common.py:70` — `"positive: הסכום נטו..."` — English prefix.
Fix: remove.

**🟡 `data_entry_common.py:72` — English prefix in error message**
`file: services/data_entry_common.py:72` — `"expense_category: חובה לציין..."` — English prefix.
Fix: remove.

**🟡 `data_entry_common.py:78` — English prefix in error message**
`file: services/data_entry_common.py:78` — `"counterparty_id: חשבונית מס..."` — English prefix.
Fix: remove.

**🟡 `data_entry_invoices.py:55` — English prefix in error message**
`file: services/data_entry_invoices.py:55` — `"not found: פריט עבודה..."` — English prefix.
Fix: remove.

**🟡 `data_entry_invoices.py:88` — English prefix in error message**
`file: services/data_entry_invoices.py:88` — `"already exists: מספר חשבונית..."` — English prefix.
Fix: remove.

**🟡 `data_entry_invoices.py:103` — English audit note (not user-facing but worth flagging)**
`file: services/data_entry_invoices.py:103` — `note="Auto-transitioned on first invoice entry"` — audit notes are exposed via the audit trail API which surfaces to UI. Should be in Hebrew.
Fix: `note="מעבר אוטומטי בעת הוספת חשבונית ראשונה"`.

**🟡 `data_entry_invoice_update.py:63` — English prefix in error message**
`file: services/data_entry_invoice_update.py:63` — `"already exists: מספר חשבונית..."` — English prefix.
Fix: remove.

**🟡 `intake.py:56` — English prefix in error message**
`file: services/intake.py:56` — `"Business not found: עסק..."` — English prefix.
Fix: remove.

**🟡 `intake.py:68` — English prefix in error message**
`file: services/intake.py:68` — `"already exists: פריט עבודה..."` — English prefix.
Fix: remove.

**🟡 `intake.py:115` — English prefix in error message**
`file: services/intake.py:115` — `"not found: פריט עבודה..."` — English prefix.
Fix: remove.

**🟡 `intake.py:119` — English prefix in error message**
`file: services/intake.py:119` — `"Cannot mark materials complete: לא ניתן..."` — English prefix.
Fix: remove.

**🟡 `filing.py:31` — English status value embedded in Hebrew message**
`file: services/filing.py:31` — `f"לא ניתן להגיש מסטטוס {item.status.value}. נדרש READY_FOR_REVIEW."` — `READY_FOR_REVIEW` is English and will surface to users.
Fix: replace with Hebrew equivalent, e.g. `"נדרש סטטוס 'מוכן לבדיקה'"`.

**🟡 `routes_business_summary.py:51` — exception detail leaks raw Python exception as string**
`file: api/routes_business_summary.py:51` — `detail=str(exc)` on `ImportError` will expose raw Python exception text to the client.
Fix: replace with a Hebrew message string.

---

## Summary Table

| Category               | Status | Count |
| ---------------------- | ------ | ----- |
| Model↔Schema sync      | ⚠️     | 5     |
| Layer separation       | ⚠️     | 4     |
| Duplicate code         | ⚠️     | 2     |
| File naming            | ⚠️     | 2     |
| Global extraction      | ⚠️     | 1     |
| Constants              | ⚠️     | 2     |
| File size              | ⚠️     | 3     |
| Completeness           | ❌     | 5     |
| Dead code              | ⚠️     | 3     |
| Pagination             | ⚠️     | 3     |
| Israeli domain logic   | ⚠️     | 3     |
| Response consistency   | ⚠️     | 2     |
| Authorization          | ❌     | 5     |
| Soft delete            | ❌     | 3     |
| Error message language | ⚠️     | 15    |

### Blocking issues (🔴)

1. `intake.py` — `period_type` never passed to `work_item_repo.create()` → `TypeError` at runtime on every work item creation
2. `data_entry_common.py` — `recalculate_totals` passes only 3 args to `update_vat_totals` which requires 5 → `TypeError` on every invoice mutation
3. All query, intake, data-entry, and filing endpoints missing `require_role` — any authenticated user can create/read/mutate VAT data
4. All `VatClientSummaryRepository` queries missing `deleted_at` filter — soft-deleted items pollute business summaries
