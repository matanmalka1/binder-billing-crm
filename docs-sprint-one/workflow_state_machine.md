# Binder & Billing CRM
## Workflow State Machine

---

## 1. Purpose
Define allowed lifecycle transitions for binders and billing records.

---

## 2. Binder Lifecycle
States:
1. `in_office`
2. `ready_for_pickup`
3. `returned`
4. `overdue`

Entry action:
1. On receive: create binder in `in_office`.
2. Set `expected_return_at = received_at + 90 days`.
3. Insert status log from `null` to `in_office`.

Allowed transitions:
1. `in_office -> ready_for_pickup`
2. `in_office -> overdue`
3. `ready_for_pickup -> returned`
4. `ready_for_pickup -> overdue`
5. `overdue -> returned`

Disallowed transitions:
1. `returned -> any`
2. `in_office -> returned` (must pass through return flow and pickup name validation)

Transition rules:
1. `returned` requires non-empty `pickup_person_name`.
2. Every transition writes one `binder_status_logs` row.
3. Overdue transition can be automatic (scheduled job) or manual admin action.

---

## 3. Client Lifecycle
States:
1. `active`
2. `frozen`
3. `closed`

Allowed transitions:
1. `active -> frozen`
2. `frozen -> active`
3. `active -> closed`
4. `frozen -> closed`

Rules:
1. `closed` is terminal.
2. Closing client sets `closed_at`.
3. Closed clients cannot receive new binders or charges.

---

## 4. Charge Lifecycle
States:
1. `draft`
2. `issued`
3. `paid`
4. `overdue`

Allowed transitions:
1. `draft -> issued`
2. `issued -> paid`
3. `issued -> overdue`
4. `overdue -> paid`

Rules:
1. Invoice generation occurs after `issued`.
2. `paid_at` set only when moving to `paid`.

---

## 5. Invoice Lifecycle (External Document Linkage)
State model:
1. `pending_external_generation`
2. `generated`
3. `sent_to_client`

Rules:
1. `external_invoice_id` set only at `generated`.
2. `invoice_url` may be null until provider response includes URL.
3. Provider failures keep invoice in `pending_external_generation`.

---

## 6. Notification Workflow
Trigger events:
1. Binder received
2. Ready for pickup
3. Binder overdue
4. Payment reminder

Rules:
1. Disabled notifications skip send and still log skip reason.
2. All attempts produce a `notifications` row.

---

*End of Workflow State Machine*
