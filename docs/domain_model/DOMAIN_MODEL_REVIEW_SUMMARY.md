## Scope
This file owns only:
- Review findings and known documentation or implementation gaps at the time of the review.

This file must not contain:
- Canonical domain behavior.
- New product requirements.
- Migration instructions.

Source of truth: reference

# Domain Model Review Summary

Last verified from code, migrations, routers, and OpenAPI for scoped claims: 2026-05-29.

Scope: current-state verification of backend domain gaps for an Israeli accounting office workflow system.

This file intentionally does not rely on module README files. It is based on ORM models, services, repositories, API routes, migrations, and tests.

## Verified Implemented

- `Person`, `LegalEntity`, `ClientRecord`, and `PersonLegalEntityLink` exist as separate first-class models.
  - Code: `app/clients/models/person.py`, `app/clients/models/legal_entity.py`, `app/clients/models/client_record.py`, `app/clients/models/person_legal_entity_link.py`
  - Migration: `alembic/versions/bfaed5b29bd3_initial.py`
- `ClientRecord` is the office workflow anchor and points to `LegalEntity`.
- `Business` belongs to `LegalEntity`; it is operational activity, not a second legal identity.
- VAT, annual reports, and advance payments have a hard `tax_calendar_entry_id` FK.
  - Code: `app/vat_reports/models/vat_work_item.py`, `app/annual_reports/models/annual_report_model.py`, `app/advance_payments/models/advance_payment.py`
- Creation flows materialize and link tax calendar entries.
  - Code: `app/tax_calendar/services/materialization_service.py`
- Onboarding creates VAT work items, advance payments, annual reports, and an initial binder.
  - Code: `app/clients/services/client_onboarding_orchestrator.py`
  - Tests: `tests/clients/service/test_client_onboarding_orchestrator.py`
- `entity_type` changes are advisor-only.
  - Code: `app/clients/services/client_update_service.py`
  - Tests: `tests/clients/service/test_entity_type_change_guard.py`
- Closing/freezing a client cancels open VAT work items and open annual reports, and closes in-office binders.
  - Code: `app/clients/services/client_update_service.py`
  - Code: `app/vat_reports/services/client_status_service.py`
  - Code: `app/annual_reports/services/client_status_service.py`
- VAT and annual report terminal `canceled` states exist.
  - Code: `app/vat_reports/models/vat_enums.py`
  - Code: `app/annual_reports/models/annual_report_enums.py`
- Notification delivery has real SendGrid and 360dialog adapters, with config gating.
  - Code: `app/infrastructure/notifications.py`
  - Code: `app/notification/services/notification_delivery_service.py`
- Tasks are persisted and have CRUD, complete, cancel, and source linking.
  - Code: `app/tasks/models/task.py`
  - Code: `app/tasks/services/task_service.py`
  - Code: `app/tasks/api/routes.py`
- Work queue aggregates system work and manual tasks, with per-client filtering and summary.
  - Code: `app/work_queue/services/work_queue_service.py`
  - Code: `app/work_queue/api/routes.py`

## Verified Open Gaps

### 1. `entity_type` change still does not reconcile existing workflow snapshots

Although secretary access is blocked, advisor changes only log/audit and regenerate obligations best-effort. Existing annual reports and workflow items keep snapshots such as:

- `AnnualReport.client_type`
- `AnnualReport.form_type`
- `VatWorkItem.period_type`

No service reconciles, flags, or forces review of existing open workflow rows after legal entity classification changes.

### 2. Client soft-delete has no downstream lifecycle policy

`ClientLifecycleService.delete_client()` only soft-deletes the `ClientRecord` and writes audit. It does not cancel or close downstream records.

Verified affected domains include:

- VAT work items
- annual reports
- reminders
- charges
- binders
- signature requests
- notifications

Client close/freeze has partial handling; soft-delete does not.

### 3. Reminder execution is not implemented and is not scheduled

`ReminderExecutorService.fire_due()` exists, but `_execute()` always marks due reminders as `FAILED` with unsupported-operation messages.

The application lifespan schedules only signature-request expiry. It does not schedule `ReminderExecutorService.fire_due()`.

Code:

- `app/reminders/services/reminder_executor_service.py`
- `app/core/background_jobs.py`
- `app/lifespan.py`

### 4. Invoice provider integration is incomplete

The invoice domain stores external invoice references, but:

- there is no invoice HTTP router
- `BillingService.issue_charge()` does not call an external provider
- `InvoiceService.attach_invoice_to_charge()` is manual/internal only
- `INVOICE_PROVIDER_*` config is present but not used by a provider client

Code:

- `app/invoice/services/invoice_service.py`
- `app/charge/services/billing_service.py`
- `app/config.py`

### 5. Notification live delivery is disabled in production config

SendGrid and WhatsApp adapters exist, but `render.yaml` sets:

```yaml
NOTIFICATIONS_ENABLED: "false"
```

With that setting, email sends are logged as disabled and treated as success. WhatsApp requires separate 360dialog config.

### 6. Reminders are not client-owned and cannot be bulk-canceled by client

Reminder rows have source metadata but no explicit `client_record_id` / `business_id` columns. There is no repository/service method to cancel scheduled reminders by client lifecycle.

Code:

- `app/reminders/models/reminder.py`
- `app/reminders/repositories/reminder_repository.py`
- `app/reminders/services/reminder_service.py`

### 7. Accounting-office core modules are absent

No backend domain exists for full bookkeeping or payroll workflows:

- journal entries / ledger / trial balance
- bank reconciliation
- payroll and employer reporting
- withholding reports such as 102, 126, 856 as first-class workflows
- capital statement / wealth declaration workflow
- direct filing/integration with Israeli authorities
- client self-service portal

This was verified by the absence of corresponding domain packages and routes under `app/`.

### 8. Client-sidebar alert counts are not exposed as a batched navigation surface

The backend exposes per-client notification summary:

- `GET /api/v1/notifications/summary?client_record_id=...`

The backend does not expose `GET /api/v1/work-queue/summary`. The current work-queue endpoint is `GET /api/v1/work-queue`; its response includes `summary` for the filtered result set.

There is no batched endpoint for alert counts across the sidebar client list. A per-row request pattern would not be appropriate for the sidebar.
