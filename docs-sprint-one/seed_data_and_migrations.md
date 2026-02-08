# Binder & Billing CRM
## Seed Data and Migration Strategy

---

## 1. Purpose
Provide migration ordering, rollback rules, and minimal seed data for local/dev/staging setup.

---

## 2. Migration Principles
1. Migrations are immutable after merge.
2. Every migration must support rollback.
3. Use explicit names with sortable timestamp prefix.
4. DDL and data backfills should be separate when possible.
5. Never drop production data in routine migrations.

---

## 3. Recommended Migration Order
1. `users`
2. `clients`
3. `binders`
4. `binder_status_logs`
5. `permanent_documents`
6. `charges`
7. `invoices`
8. `notifications`
9. `system_settings`
10. indexes and constraints

---

## 4. Core Constraints Checklist
1. Integer auto-increment PK on all `id` columns.
2. Unique `users.email`.
3. Unique `clients.id_number`.
4. Partial unique index for active binder by `binder_number`.
5. FK integrity for all parent-child tables.

---

## 5. Seed Data (Minimum)
## 5.1 Users
1. Advisor test user.
2. Secretary test user.

## 5.2 System Settings
1. `binder_max_days = 90`
2. `reminder_day_1 = 75`
3. `reminder_day_2 = 90`

## 5.3 Optional Sample Domain Data
1. 3 sample clients.
2. 2 active binders.
3. 1 overdue binder.
4. 2 sample charges and 1 invoice.

---

## 6. Environment Policy
1. Local: allow reseed from scratch.
2. Staging: seed baseline users/settings only.
3. Production: no synthetic client/financial seed data.

---

## 7. Operational Commands (Abstract)
1. `migrate up`
2. `migrate down <version>`
3. `seed baseline`
4. `seed demo` (non-production only)

---

## 8. Verification After Migration
1. Confirm all tables exist.
2. Confirm constraints and indexes exist.
3. Run smoke query for each FK chain.
4. Confirm ID sequences produce `1, 2, 3...` on empty DB.

---

*End of Seed Data and Migration Strategy*
