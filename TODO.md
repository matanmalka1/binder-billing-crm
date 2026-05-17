# TODO - Verified System Gaps

Last verified from code, migrations, and tests: 2026-05-17.

## Critical

- [ ] Add reconciliation for `entity_type` changes.
  - Current state: advisor-only guard exists, but existing `AnnualReport.client_type`, `AnnualReport.form_type`, and `VatWorkItem.period_type` snapshots are not reconciled or flagged.
  - Relevant code: `app/clients/services/client_update_service.py`, `app/annual_reports/models/annual_report_model.py`, `app/vat_reports/models/vat_work_item.py`

- [ ] Add downstream lifecycle handling for client soft-delete.
  - Current state: `delete_client()` soft-deletes only `ClientRecord`; close/freeze has partial downstream handling, delete does not.
  - Must decide per domain: cancel, close, archive, preserve read-only, or block delete.
  - Relevant code: `app/clients/services/client_lifecycle_service.py`

- [ ] Implement and schedule reminder execution.
  - Current state: `ReminderExecutorService._execute()` always fails reminders as unsupported, and app lifespan schedules only signature-request expiry.
  - Relevant code: `app/reminders/services/reminder_executor_service.py`, `app/core/background_jobs.py`, `app/lifespan.py`

- [ ] Add client-scoped reminder cancellation.
  - Current state: `Reminder` has no explicit `client_record_id` / `business_id`, and there is no `cancel_scheduled_by_client` service path.
  - Relevant code: `app/reminders/models/reminder.py`, `app/reminders/repositories/reminder_repository.py`

## High

- [ ] Complete invoice provider integration.
  - Current state: invoice references can be attached internally, but there is no invoice API, provider client, or call from `BillingService.issue_charge()`.
  - Relevant code: `app/invoice/services/invoice_service.py`, `app/charge/services/billing_service.py`, `app/config.py`

- [ ] Decide and enable production notification delivery.
  - Current state: SendGrid/WhatsApp adapters exist, but `render.yaml` sets `NOTIFICATIONS_ENABLED=false`.
  - Relevant code: `app/infrastructure/notifications.py`, `app/notification/services/notification_delivery_service.py`, `render.yaml`

- [ ] Add batched alert counts for client sidebar navigation.
  - Current state: notification/work-queue summaries exist per client, but no batched endpoint exists for all sidebar clients.
  - Relevant code: `app/notification/api/notifications.py`, `app/work_queue/api/routes.py`, `../frontend/src/components/layout/ClientSidebar/ClientSidebar.tsx`

## Product Scope Gaps

- [ ] Add bookkeeping core if this system must become a full accounting-office platform.
  - Missing domains: journal entries, ledger, trial balance, bank reconciliation.

- [ ] Add payroll workflows if the office manages payroll.
  - Missing domains: employees, payslips, employer reports, payroll payments.

- [ ] Add withholding-report workflows.
  - Missing first-class workflows: 102, 126, 856.

- [ ] Add capital statement / wealth declaration workflow.

- [ ] Add direct authority filing/integration layer.
  - Missing live filing/status integrations with Israeli authorities.

- [ ] Add client self-service portal.
  - Missing client login, document upload by client, task/status visibility, and approval flows outside public signature links.
