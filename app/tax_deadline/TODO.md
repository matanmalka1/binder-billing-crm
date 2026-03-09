## [P2] 7.1 — ציר זמן הגשות (Filing Timeline Visualization)
**Status:** PARTIAL
**Gap:** `TaxDeadline` records have `due_date` and `status` but no endpoint returns them sorted as an ordered milestone timeline with contextual labels.
**Files to touch:**
- `app/tax_deadline/api/tax_deadline.py` — add `GET /tax-deadlines/timeline?client_id=` endpoint returning deadlines sorted by `due_date` with `days_remaining` and `milestone_label`
- `app/tax_deadline/services/tax_deadline_service.py` — add `get_timeline(client_id)` computing `days_remaining = (due_date − today).days` and attaching labels
- `app/tax_deadline/schemas/tax_deadline.py` — add `TimelineEntry` schema with `due_date`, `deadline_type`, `status`, `days_remaining`, `milestone_label`
**Acceptance criteria:** Timeline endpoint returns deadlines ordered by `due_date` asc, each entry includes `days_remaining` (negative if overdue) and a human-readable `milestone_label`.
