# שלב 5 — Client → Person + LegalEntity + ClientRecord migration

## Context

`Client` deprecated. Goal: replace all usage with three-layer arch: `Person` + `LegalEntity` + `ClientRecord`. DB empty both dev + prod — no data migration needed. `Client` deleted only after all usages replaced and tests pass.

One sub-step at a time. Tests must pass before next sub-step.

---

## Current state (verified)

- ✅ `Person` already has phone, email, address_* fields (person.py:23-30) — **5.1 already done**
- ✅ `ClientRecord` already has notes, accountant_name (client_record.py:18-20) — **5.2 already done**
- ✅ `PersonLegalEntityLink` exists with OWNER role default (person_legal_entity_link.py:24)
- ✅ `LegalEntity.official_name` NOT NULL (completed in שלב 3)
- ✅ `Business.legal_entity_id` column exists alongside `client_id` (business.py:38)
- ⚠️ `Business.client_id` still active FK + `Business.client` relationship + contact_phone/contact_email properties depend on it

---

## Files per sub-step

### 5.1 — Person fields — SKIP
Already present. Verify via `Read app/clients/models/person.py`. No migration needed.

### 5.2 — ClientRecord.notes — SKIP
Already present. Verify via `Read app/clients/models/client_record.py`. No migration needed.

### 5.3 — ClientCreationService dual flow

**5.3 pre-step: caller audit** (design return shape correctly first time)
```bash
grep -rn "create_client\|ClientCreationService" --include="*.py" app/ tests/
```
Analyze results → decide final return shape now (will survive into 5.8 unchanged):
- If callers only need `ClientRecord` → return `ClientRecord`
- If callers need Person too → return `tuple[Person, ClientRecord]`
- If callers currently destructure `(Client, ClientRecord)` → transition via returning both `(Client, ClientRecord)` in 5.3 (same shape as now) then strip Client in 5.8 — avoid only if caller count is small enough to update twice

Add Person + PersonLegalEntityLink creation alongside existing Client. Keep Client creation untouched.

**Files to modify:**
- [app/clients/services/client_creation_service.py](app/clients/services/client_creation_service.py) — add Person + link creation after LegalEntity creation, before ClientRecord. Final return shape per audit above.
- [app/clients/repositories/legal_entity_repository.py](app/clients/repositories/legal_entity_repository.py) — accept `official_name` in `create()` (currently missing — will fail NOT NULL)
- [app/clients/repositories/person_repository.py](app/clients/repositories/person_repository.py) — **create new** (repo layer for Person + link)
- All callers identified by audit — update if return shape changes

**Verification:**
- `tests/clients/service/test_client_creation_service.py` — must pass
- After create, assert 1 Person, 1 LegalEntity, 1 link(OWNER), 1 ClientRecord, 1 Client all consistent

### 5.4 — Replace Client JOINs in repositories (5 files, in order)

Each file: run tests for that domain after change.

1. [app/vat_reports/repositories/vat_compliance_repository.py](app/vat_reports/repositories/vat_compliance_repository.py) — L32, L71, L94: `JOIN Client` → `JOIN LegalEntity`
2. [app/annual_reports/repositories/report_repository.py](app/annual_reports/repositories/report_repository.py) — L158: same
3. [app/timeline/services/timeline_client_aggregator.py](app/timeline/services/timeline_client_aggregator.py) — L28: `query(Client)` → `LegalEntityRepository.get_by_id()`
4. [app/businesses/repositories/business_repository_read.py](app/businesses/repositories/business_repository_read.py) — L30: `JOIN Client` via `Business.client_id` → `JOIN LegalEntity` via `Business.legal_entity_id`
5. [app/clients/repositories/client_repository.py](app/clients/repositories/client_repository.py) — 9 query methods → operate on ClientRecord+LegalEntity. Rename to `ClientRecordRepository` methods (merge into existing repo) after complete.

**Blocker for #4**: `Business.legal_entity_id` is nullable. Before swapping JOIN, need all rows populated. Check if existing fixtures/seed populate it — if not, backfill in test fixtures as part of this step.

### 5.5 — notification_send_service rewrite

[app/notification/services/notification_send_service.py](app/notification/services/notification_send_service.py)

- L53-64 `_get_business_and_client`: `Business → LegalEntity → PersonLegalEntityLink → Person`, return `(Business, Person)` instead of `(Business, Client)`
- L66-71 `_get_client`: `ClientRecord → LegalEntity → PersonLegalEntityLink → Person`
- L253-254, 285-287: same pattern
- Fallback: if no linked Person, phone/email = None, log and return True (no raise)

Type signatures change from `Client` to `Person`. Update all callers within file.

### 5.6 — ClientRecordResponse schema

**New file:** [app/clients/schemas/client_record_response.py](app/clients/schemas/client_record_response.py)
- `ClientRecordResponse` (fields from plan prompt)
- `ClientRecordListResponse`
- `CreateClientRecordResponse`

**Modified:**
- [app/clients/api/clients.py](app/clients/api/clients.py) — swap `response_model=ClientResponse` → `ClientRecordResponse` at L75, L117-119, L147, L158-163, L186-201, L223-230
- [app/clients/api/client_enrichment.py](app/clients/api/client_enrichment.py) — `enrich_single/enrich_list` accept `ClientRecordResponse`

Need new query path in service layer (or keep response builder inside api router) that joins ClientRecord + LegalEntity + Person → response.

### 5.7 — Remove Business.client_id FK

[app/businesses/models/business.py](app/businesses/models/business.py)
- L36: remove `client_id` column
- L41: remove `client = relationship("Client", ...)`
- L89, L94, L99: `full_name`, `contact_phone`, `contact_email` properties rely on `self.client` — rewrite to use `self.legal_entity.official_name` + Person-via-link lookup OR remove properties if unused elsewhere (audit usages first)
- L103: remove `client_id` from `__repr__`
- L108: remove `Index("ix_business_client_id", "client_id")`
- L111-114: `ix_business_client_name_active` uses `client_id` — replace with `legal_entity_id`

**New migration:** `alembic revision --autogenerate -m "remove client_id from businesses"`

**Precondition:** 5.4 step #4 must be done (JOIN now on `legal_entity_id`), and all callers of `Business.client` / `business.full_name` / `contact_*` updated.

### 5.8 — Delete Client

Gate check:
```bash
grep -rn "from app.clients.models.client import" --include="*.py" . | grep -v "client.py"
# expected: no output
```

If clean:
- Delete [app/clients/models/client.py](app/clients/models/client.py)
- New migration: `alembic revision -m "drop clients table"` + manual `op.drop_table('clients')`
- Drop `Client` relationship from any other model (search)
- Full test suite green

---

## Critical files touched (summary)

Models:
- `app/clients/models/person.py` (verify only)
- `app/clients/models/client_record.py` (verify only)
- `app/clients/models/legal_entity.py` (already done)
- `app/businesses/models/business.py` (5.7)
- `app/clients/models/client.py` (delete in 5.8)

Repositories:
- `app/clients/repositories/legal_entity_repository.py` (5.3)
- `app/clients/repositories/client_record_repository.py` (5.4 merge)
- `app/clients/repositories/client_repository.py` (5.4 rewrite/rename)
- `app/clients/repositories/person_repository.py` (5.3 new)
- `app/vat_reports/repositories/vat_compliance_repository.py` (5.4)
- `app/annual_reports/repositories/report_repository.py` (5.4)
- `app/businesses/repositories/business_repository_read.py` (5.4)

Services:
- `app/clients/services/client_creation_service.py` (5.3)
- `app/timeline/services/timeline_client_aggregator.py` (5.4)
- `app/notification/services/notification_send_service.py` (5.5)

API + schemas:
- `app/clients/schemas/client_record_response.py` (5.6 new)
- `app/clients/api/clients.py` (5.6)
- `app/clients/api/client_enrichment.py` (5.6)

Migrations (3 new):
- `NNNN_remove_client_id_from_businesses.py` (5.7)
- `NNNN_drop_clients_table.py` (5.8)
- (5.1 + 5.2 skipped — no schema change)

---

## Verification

After each sub-step:
```bash
JWT_SECRET=test-secret pytest -q tests/<relevant_domain>/
```

After 5.8:
```bash
JWT_SECRET=test-secret pytest -q
# full suite green = Client fully removed
```

Pre-existing `client_id` refactor failures are known — ignore unless blocking.

---

## Decisions (resolved)

1. **LegalEntityRepository.create official_name param** — fix in 5.3 (scope fits, single touchpoint).
2. **ClientRecordResponse.id** — break. `id = ClientRecord.id` canonical. Frontend updates if it consumes raw id.
3. **Business.contact_phone/contact_email/full_name** — audit callers first in 5.7 (pre-step), then decide: rewrite to use legal_entity + Person link OR drop fallback.

## 5.7 pre-step: audit Business property callers

```bash
grep -rn "\.contact_phone\|\.contact_email" --include="*.py" app/
grep -rn "business\.full_name\|\.business\.full_name" --include="*.py" app/
grep -rn "\.client\." --include="*.py" app/businesses/ app/notification/ app/binders/
```

**Rule**: if callers exist → rewrite props to `legal_entity + Person-via-link` (preserve fallback semantics). Do NOT drop fallback silently.

## 5.8 — ClientCreationService full cleanup

In addition to deleting `client.py` + dropping table, 5.8 MUST:
- Remove Client creation from `client_creation_service.py` entirely (the dual-flow added in 5.3)
- End state: `ClientCreationService` creates **Person + LegalEntity + PersonLegalEntityLink + ClientRecord only** — zero `Client` reference
- Remove `_create_client_with_generated_office_number` helper; office_client_number now generated on ClientRecord directly
- Remove `ClientRepository` import + usage
- Return signature changes from `tuple[Client, ClientRecord]` → `ClientRecord` (or `tuple[Person, ClientRecord]` if callers need Person)

Caller audit required before 5.8:
```bash
grep -rn "create_client\|ClientCreationService" --include="*.py" app/ tests/
```

Update all callers to unpack new return shape.
