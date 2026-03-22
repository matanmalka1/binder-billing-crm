# Users Module

> Last audited: 2026-03-22
> Audit basis: source review (`app/users/**`) + test run (`pytest tests/auth tests/users -q`) => 47 passed.

Manages authentication, user lifecycle administration, role-based access checks, and user audit logs.

## Audit Summary

Current status after this audit:
- No critical or high-severity defects identified in the users domain implementation.
- Authentication, token invalidation, role gating, and audit logging flows are covered by passing API/service tests.
- Documentation drift existed and was corrected in this file (paths, test inventory, and behavior notes).

Known gaps and hardening opportunities:
- Login has no built-in rate limiting/account lockout in this module.
- `JWT_SECRET` rotation/revocation strategy is not documented here.
- Audit log query accepts `from`/`to` without validating `from <= to`.
- Duplicate-email handling is service-level pre-check + DB unique constraint; concurrent create conflicts may surface as DB errors if not normalized globally.

## Scope

This module provides:
- Login/logout with JWT-based authentication.
- Auth token handling via `Authorization: Bearer` and HttpOnly cookie (`access_token`).
- Advisor-only user management APIs (create/list/get/update/activate/deactivate/reset password).
- Token invalidation via `token_version` bumps (logout, deactivate, password reset).
- User audit logging for authentication and management actions.
- Audit log querying with filters + pagination.

## Domain Model

`User` fields:
- `id` (PK)
- `full_name` (required)
- `email` (unique, required)
- `phone` (optional)
- `password_hash` (required, bcrypt hash)
- `role` (enum: `advisor`, `secretary`)
- `is_active` (default `true`)
- `token_version` (default `0`)
- `created_at`
- `last_login_at` (optional)

`UserAuditLog` fields:
- `id` (PK)
- `action` (enum)
- `actor_user_id` (optional FK)
- `target_user_id` (optional FK)
- `email` (optional)
- `status` (enum: `success`, `failure`)
- `reason` (optional)
- `metadata_json` (optional JSON string)
- `created_at`

Audit action enum values:
- `login_success`
- `login_failure`
- `logout`
- `user_created`
- `user_updated`
- `user_activated`
- `user_deactivated`
- `password_reset`

Implementation references:
- Models: `app/users/models/user.py`, `app/users/models/user_audit_log.py`
- Schemas: `app/users/schemas/auth.py`, `app/users/schemas/user_management.py`
- Repositories: `app/users/repositories/user_repository.py`, `app/users/repositories/user_audit_log_repository.py`
- Services: `app/users/services/auth_service.py`, `app/users/services/user_management_service.py`, `app/users/services/audit_log_service.py`
- API: `app/users/api/auth.py`, `app/users/api/users.py`, `app/users/api/users_audit.py`, `app/users/api/deps.py`

## API

Routers are mounted under `/api/v1`.

### Auth endpoints

#### Login
- `POST /api/v1/auth/login`
- Public endpoint
- Body supports `rememberMe` (camelCase alias) and `remember_me` (snake_case).
- Response includes:
  - `token` (JWT)
  - `user` (`id`, `full_name`, `role`, `email`)
- Also sets HttpOnly cookie:
  - `access_token`
  - `SameSite=lax` in non-production, `none` in production
  - `secure=true` in production

#### Logout
- `POST /api/v1/auth/logout`
- Requires authenticated user
- Returns `204 No Content`
- Invalidates active tokens by bumping user `token_version`
- Deletes `access_token` cookie

### User management endpoints (advisor-only)

Base prefix: `/api/v1/users`

- `POST /api/v1/users` create user
- `GET /api/v1/users` list users (`page`, `page_size`, `is_active`)
- `GET /api/v1/users/{user_id}` get user
- `PATCH /api/v1/users/{user_id}` partial update (`full_name`, `phone`, `role`, `email`)
- `POST /api/v1/users/{user_id}/activate` activate user
- `POST /api/v1/users/{user_id}/deactivate` deactivate user (cannot deactivate self; bumps `token_version`)
- `POST /api/v1/users/{user_id}/reset-password` reset password (bumps `token_version`)

### Audit logs endpoint (advisor-only)

- `GET /api/v1/users/audit-logs`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)
  - `action`
  - `target_user_id`
  - `actor_user_id`
  - `email`
  - `from` (datetime, alias for `from_ts`)
  - `to` (datetime, alias for `to_ts`)

## Behavior Notes

- Auth dependency checks bearer token first; if absent, falls back to `access_token` cookie.
- Token payload must decode and then pass runtime checks for `sub` and `tv` against DB user state.
- Inactive users cannot log in and cannot pass current-user dependency checks.
- `rememberMe=true` doubles token TTL (`JWT_TTL_HOURS * 2`).
- Password validation requires minimum length of 8 characters.
- Duplicate email in create/update raises `USER.CONFLICT`.
- Empty update payloads and immutable-field update attempts are rejected.
- Auth and user-management actions are written to `user_audit_logs`.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`:
- `detail`
- `error`
- `error_meta`

Users domain service errors include:
- `USER.CONFLICT`
- `USER.FORBIDDEN`
- `USER.INVALID_PASSWORD`
- `USER.INVALID_UPDATE`
- `USER.NO_FIELDS_PROVIDED`
- `USER.NOT_FOUND`

## Cross-Domain Integration

- `app/main.py` mounts auth/users routers.
- Role enforcement is shared through `app/users/api/deps.py`.
- Global exception handling/envelope is provided by `app/core/exceptions.py`.

## Tests

Auth + users suites:
- `tests/auth/api/test_auth.py`
- `tests/auth/api/test_logout_invalidation.py`
- `tests/auth/service/test_jwt_expiration.py`
- `tests/users/api/test_auth_deps.py`
- `tests/users/api/test_auth_endpoints.py`
- `tests/users/api/test_user_audit_logs.py`
- `tests/users/api/test_user_management.py`
- `tests/users/api/test_user_reset_password.py`
- `tests/users/api/test_user_token_invalidation.py`
- `tests/users/models/test_user_model.py`
- `tests/users/repository/test_user_repository.py`
- `tests/users/schemas/test_user_management_schema.py`
- `tests/users/services/test_audit_log_service.py`
- `tests/users/services/test_auth_service.py`
- `tests/users/services/test_auth_service_additional.py`
- `tests/users/services/test_user_management_policies.py`
- `tests/users/services/test_user_management_service_additional.py`
- `tests/users/services/test_user_management_service_list_reset.py`

Run this domain:

```bash
pytest tests/auth tests/users -q
```
