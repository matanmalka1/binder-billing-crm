# Frontend Roles Matrix (Advisor vs Secretary)

Role values returned by login:

- `advisor`
- `secretary`

`advisor` is a super-role.

## Global Rules

- If an endpoint is `advisor`-only, the API returns `403` to a `secretary`.
- UI hides `advisor`-only actions for `secretary`.
- UI does not implement authorization logic beyond reading `user.role` from login and reacting to `403` responses.

## Endpoint Visibility and Behavior

### Unauthenticated

- `GET /health` (no auth)
- `GET /info` (no auth)
- `GET /` (no auth)
- `POST /api/v1/auth/login` (no auth)

### Authenticated: Both Roles (`advisor` and `secretary`)

Clients:

- `POST /api/v1/clients`
- `GET /api/v1/clients` (paginated)
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
  - `secretary` cannot set `status` to `frozen` or `closed` (service enforces; API returns `403`)

Binders:

- `POST /api/v1/binders/receive`
- `POST /api/v1/binders/{binder_id}/return`
- `GET /api/v1/binders` (not paginated)
- `GET /api/v1/binders/{binder_id}`

Operational binder lists (paginated):

- `GET /api/v1/binders/open`
- `GET /api/v1/binders/overdue`
- `GET /api/v1/binders/due-today`
- `GET /api/v1/clients/{client_id}/binders`

Binder history:

- `GET /api/v1/binders/{binder_id}/history`

Dashboards:

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/work-queue` (paginated)
- `GET /api/v1/dashboard/alerts`
- `GET /api/v1/dashboard/attention`
  - `secretary` receives attention items without `item_type == "unpaid_charge"`

Search:

- `GET /api/v1/search` (paginated)

Timeline:

- `GET /api/v1/clients/{client_id}/timeline` (paginated)
  - Timeline charge events include `metadata.amount` and are returned for both roles.

Permanent documents:

- `POST /api/v1/documents/upload` (`multipart/form-data`)
- `GET /api/v1/documents/client/{client_id}`
- `GET /api/v1/documents/client/{client_id}/signals`

Charges (read-only for secretary; read/write for advisor described below):

- `GET /api/v1/charges` (paginated)
  - `advisor` items include `amount` and `currency`
  - `secretary` items exclude `amount` and `currency`
- `GET /api/v1/charges/{charge_id}`
  - `advisor` response includes `amount` and `currency`
  - `secretary` response excludes `amount` and `currency`

### Authenticated: Advisor-Only (`advisor`)

Dashboards:

- `GET /api/v1/dashboard/overview`

Charges (write):

- `POST /api/v1/charges`
- `POST /api/v1/charges/{charge_id}/issue`
- `POST /api/v1/charges/{charge_id}/mark-paid`
- `POST /api/v1/charges/{charge_id}/cancel`

## UI Hidden vs Disabled

UI behavior is role-driven:

- Advisor-only pages/actions (overview dashboard, charge writes) are hidden for `secretary`.
- If a `secretary` navigates directly to an advisor-only route and the API returns `403`, UI renders an “Access denied” state and does not retry.

