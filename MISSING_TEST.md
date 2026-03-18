# Missing Tests Report

Updated on March 18, 2026.

Audit basis:
- Full suite run: `586 passed, 1 skipped, 0 failed`
- Coverage source: `./.venv/bin/python -m coverage run -m pytest -q`
- Coverage snapshot (app-only): `98%` (`8805` statements, `209` missing)
- This file tracks only still-open test gaps.

## 1) Removed as Covered

Closed in this cycle:

- `app/binders/services/binder_intake_service.py` -> `100%`
- `app/main.py` -> `100%`
- `app/correspondence/services/correspondence_service.py` -> `100%`
- `app/annual_reports/repositories/schedule_repository.py` -> `100%`
- `app/vat_reports/repositories/vat_invoice_repository.py` -> `100%`
- `app/config.py` -> `100%`
- `app/reminders/services/status_changes.py` -> `100%`
- `app/reminders/services/factory.py` -> `100%`

## 2) Current Critical Gaps (<85% coverage)

No files currently below `85%`.

## 3) Current High-Priority Gaps (85-90% coverage)

No files currently in the `85-90%` range.

## 4) Next Target

1. Keep the threshold at `>=90%` per file and monitor regressions in CI.
2. Prioritize modules at `91-93%` if you want to push toward `99%` app-wide.
