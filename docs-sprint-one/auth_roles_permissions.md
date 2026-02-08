# Binder & Billing CRM
## Auth, Roles, and Permissions

---

## 1. Purpose
Define authentication, authorization, and access boundaries for all system roles.

---

## 2. Authentication
1. Authentication method: email + password login.
2. Session method: JWT bearer token.
3. Token expiry: 8 hours.
4. Refresh policy: optional in Phase 1, required by Phase 2.
5. Password storage: salted hash only.

---

## 3. Roles
1. `advisor` (admin-level business owner)
2. `secretary` (operations user)

---

## 4. Permission Matrix
## 4.1 Clients
1. Create client: `advisor`, `secretary`
2. Update client basic info: `advisor`, `secretary`
3. Freeze/close client: `advisor`
4. View client financial tab: `advisor`, `secretary`

## 4.2 Binders
1. Receive binder: `advisor`, `secretary`
2. Mark ready for pickup: `advisor`, `secretary`
3. Return binder: `advisor`, `secretary`
4. View binder status logs: `advisor`, `secretary`

## 4.3 Billing
1. Create charge: `advisor`, `secretary`
2. Edit charge amount/pricing rules: `advisor`
3. Mark charge paid: `advisor`, `secretary`
4. Create/view invoices: `advisor`, `secretary`

## 4.4 Documents
1. Upload permanent documents: `advisor`, `secretary`
2. Edit document metadata: `advisor`, `secretary`
3. Remove file linkage (`file_url`): `advisor`

## 4.5 Settings and Reports
1. Update system settings: `advisor`
2. View management exceptions: `advisor`
3. View dashboard logistics widgets: `advisor`, `secretary`

---

## 5. Authorization Rules
1. Every protected endpoint requires a valid token.
2. Role check happens before request business logic.
3. Forbidden actions return `403`.
4. Inactive users (`is_active = false`) are blocked from all actions.

---

## 6. Audit Requirements
1. Log login success and failure attempts.
2. Log all binder status transitions via `binder_status_logs`.
3. Log privileged setting changes with actor and timestamp.

---

## 7. Security Baseline
1. Enforce HTTPS in non-local environments.
2. Use secure cookie flags if tokens are cookie-based.
3. Rate-limit login endpoint.
4. Enforce password complexity and lockout policy.

---

*End of Auth, Roles, and Permissions*
