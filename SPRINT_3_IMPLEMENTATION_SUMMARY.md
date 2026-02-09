# Sprint 3 Implementation Summary (Historical)

Sprint 3 billing was implemented according to the frozen requirements in `SPRINT_3_FORMAL_SPECIFICATION.md`.

This document is intentionally lightweight to avoid duplicating the canonical docs:
- API behavior: `API_CONTRACT.md`
- Setup notes: `DEV_SETUP.md`

## Delivered (Sprint 3)
- Charges and Invoices ORM entities exist in the codebase.
- Charge lifecycle enforcement at the service layer (`draft → issued → paid`, with `canceled` as a terminal state).
- Role enforcement:
  - `ADVISOR`: create/issue/mark-paid/cancel charges
  - `SECRETARY`: read-only access to charges
- Alembic introduced for the Sprint 3 billing tables (single migration):
  - `alembic/versions/001_create_billing_tables.py`

## Notes
- Sprint 3 defines invoice *attachment rules* and persistence, but the repository does not expose invoice attachment via an API endpoint (invoice behavior is enforced at the service layer).
