# Binder & Billing CRM
## Billing and Invoicing Integration Specification

---

## 1. Purpose
Define billing data flow between internal charges and external invoice provider.

---

## 2. Domain Separation
1. `charges` are internal payment requests.
2. `invoices` are external fiscal documents.
3. A charge can exist before invoice generation.

---

## 3. Billing Flows
## 3.1 Retainer Flow
1. Create monthly charge in `draft`.
2. Review and move to `issued`.
3. Generate external invoice.
4. Track payment to `paid` or `overdue`.

## 3.2 One-Time Flow
1. Create one-time charge.
2. Issue immediately or keep draft.
3. Generate invoice once issued.

---

## 4. Provider Integration Contract (Abstract)
Outbound payload fields:
1. client legal name
2. client identifier
3. amount
4. issue date
5. description

Stored response fields:
1. `external_invoice_id`
2. `provider_name`
3. `issued_at`
4. `invoice_url` (nullable)

---

## 5. Failure Handling
1. Provider timeout: retry with backoff.
2. Validation error: mark failed and require manual fix.
3. Duplicate request: use idempotency key per charge.
4. Never create two invoices for same charge unless explicit override.

---

## 6. Reconciliation
1. Daily reconciliation job compares local issued invoices and provider status.
2. Flag mismatches for advisor review.
3. Keep immutable audit trail of reconciliation actions.

---

## 7. Security and Compliance
1. Encrypt provider credentials at rest.
2. Redact sensitive values from logs.
3. Capture who initiated invoice generation.

---

*End of Billing and Invoicing Integration Specification*
