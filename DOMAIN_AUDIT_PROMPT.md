# Domain Post-Refactor Audit Prompt

## Israeli Tax Advisor CRM
## Prompt

**STOP — before doing anything, ask me: "Which domain should I audit?"
Do not read any files until I specify the domain.
Audit strictly the files under `app/{domain}/` only — do NOT read tests/, alembic/ 
**

- Output the audit report as a markdown file only — do not print findings in the chat. Save to `audit_{domain}.md` in the project root.

**Domain Post-Refactor Audit — Israeli Tax Advisor CRM**

FastAPI + SQLAlchemy backend for an Israeli tax advisor CRM (clients, businesses, binders, VAT/annual reports, charges). Large model/schema refactor just completed. Audit one domain at a time — domain will be specified.

**Checks to perform:**

1. **Model↔Schema↔Repo↔Service↔API sync** — field coverage, enum consistency, unused model fields, missing fields

2. **Layer separation** — no business logic in API/repo, no raw ORM in service

3. **Duplicate code** — repeated logic across domain files

4. **File naming** — consistent with project conventions, name reflects responsibility, split/merge candidates

5. **Global extraction** — types/enums/utils imported by 2+ domains → suggest `app/common/`, `app/utils/`, `app/core/`

6. **Constants** — magic numbers/strings/thresholds → extract to `constants.py`; flag unused constants

7. **File size** — flag files >150 lines, propose split with new names

8. **Completeness** — CRUD/lifecycle coverage, unraised error codes, blocking TODOs, broken imports

9. **Dead code** — unused imports, unreachable branches, deprecated helpers

10. **Pagination** — all list endpoints use `page`/`page_size`/`total`; defaults `page=1, page_size=20`; repo uses `_paginate()` from `BaseRepository`; no unbounded list endpoints

11. **Israeli domain logic** — missing Israeli law validations (ת.ז. checksum, VAT periods, מקדמות due dates), incorrect thresholds (OSEK PATUR ceiling, VAT rate 18%, NI brackets), missing workflow steps standard in Israeli tax practice, Hebrew/RTL handling issues

12. **Response consistency** — field names consistent with other domains (watch for `business_id` vs `client_id` drift post-refactor); datetime fields returned in uniform format across all endpoints in this domain

13. **Authorization consistency** — every endpoint declares `require_role` explicitly; sensitive operations (delete, bulk actions, financial data) restricted to `ADVISOR` only; no endpoint relies on authentication alone without role check

14. **Soft delete consistency** — every repository query filters `deleted_at.is_(None)`; no code path can accidentally return deleted records; soft delete sets both `deleted_at` and `deleted_by`

15. **Error message language** — per project rule all user-facing strings must be in Hebrew; verify every `raise AppError / NotFoundError / ConflictError / ForbiddenError` in this domain has a Hebrew `message`; flag any English string that surfaces to the user; error `code` strings (e.g. `"BINDER.NOT_FOUND"`) are exempt — those are machine codes, not user-facing

**Rules:**

- This domain only — no cross-domain changes
- Fix confirmed issues only — no speculative refactor
- Read all domain files before reporting
- Cross-domain imports allowed at Service facade level only
- Migrations are out of scope

**Output:**

- Group by category, each finding: `file:line — description — fix`
- Tag: 🔴 blocking / 🟡 should fix / 🔵 suggestion
- End with summary table:

| Category               | Status   | Count |
| ---------------------- | -------- | ----- |
| Model↔Schema sync      | ✅/⚠️/❌ | N     |
| Layer separation       | ...      | ...   |
| Duplicate code         | ...      | ...   |
| File naming            | ...      | ...   |
| Global extraction      | ...      | ...   |
| Constants              | ...      | ...   |
| File size              | ...      | ...   |
| Completeness           | ...      | ...   |
| Dead code              | ...      | ...   |
| Pagination             | ...      | ...   |
| Israeli domain logic   | ...      | ...   |
| Response consistency   | ...      | ...   |
| Authorization          | ...      | ...   |
| Soft delete            | ...      | ...   |
| Error message language | ...      | ...   |

**Specify domain now.**

---

## Domain Checklist

Track progress across all domains:

| Domain                | Status | Notes |
| --------------------- | ------ | ----- |
| `advance_payments`    | ⬜     |       |
| `annual_reports`      | ⬜     |       |
| `authority_contact`   | ⬜     |       |
| `binders`             | ⬜     |       |
| `charge`              | ⬜     |       |
| `clients`             | ⬜     |       |
| `businesses`          | ⬜     |       |
| `correspondence`      | ⬜     |       |
| `dashboard`           | ⬜     |       |
| `health`              | ⬜     |       |
| `invoice`             | ⬜     |       |
| `notification`        | ⬜     |       |
| `permanent_documents` | ⬜     |       |
| `reminders`           | ⬜     |       |
| `reports`             | ⬜     |       |
| `search`              | ⬜     |       |
| `signature_requests`  | ⬜     |       |
| `tax_deadline`        | ⬜     |       |
| `timeline`            | ⬜     |       |
| `users`               | ⬜     |       |
| `vat_reports`         | ⬜     |       |

**Status legend:** ⬜ pending · 🔄 in progress · ✅ done · ❌ has blocking issues

---

## After All Domains Complete

Once all domains pass audit:

1. Delete both DBs
2. Run fresh Alembic migration: `alembic revision --autogenerate -m "initial_schema"`
3. Review generated migration for partial index `where` clauses — wrap with `sa.text(...)`
4. Apply: `alembic upgrade head`
5. Update all domain `README.md` files to reflect post-refactor state
