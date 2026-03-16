# Users Module

Manages authentication, user lifecycle administration, role-based access checks, and user audit logs.

## Scope

This module provides:
- Login/logout with JWT-based authentication
- Auth token handling via `Authorization: Bearer` and HttpOnly cookie (`access_token`)
- Advisor-only user management APIs (create/list/get/update/activate/deactivate/reset password)
- Token invalidation via `token_version` bumps (logout, deactivate, password reset)
- User audit logging for authentication and management actions
- Audit log querying with filters + pagination

## Domain Model

`User` fields:
- `id` (PK)
- `full_name` (required)
- `email` (unique, required)
- `phone` (optional)
- `password_hash` (required)
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
- `metadata_json` (optional)
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
- Schemas: `app/users/schemas/auth.py`, `app/users/models/user_management.py`
- Repositories: `app/users/repositories/user_repository.py`, `app/users/repositories/user_audit_log_repository.py`
- Services: `app/users/services/auth_service.py`, `app/users/services/user_management_service.py`, `app/users/services/audit_log_service.py`
- API: `app/users/api/auth.py`, `app/users/api/users.py`, `app/users/api/users_audit.py`, `app/users/api/deps.py`

## API

Routers are mounted in `app/main.py` under `/api/v1`.

### Auth endpoints

#### Login
- `POST /api/v1/auth/login`
- Public endpoint
- Body:

```json
{
  "email": "advisor@example.com",
  "password": "strong-password",
  "rememberMe": true
}
```

Response includes:
- `token` (JWT)
- `user` (`id`, `full_name`, `role`)

Also sets HttpOnly cookie:
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

#### Create user
- `POST /api/v1/users`
- Role: `ADVISOR`
- Body:

```json
{
  "full_name": "New Secretary",
  "email": "secretary@example.com",
  "phone": "050-0000000",
  "role": "secretary",
  "password": "strong-password"
}
```

#### List users
- `GET /api/v1/users`
- Role: `ADVISOR`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)
  - `is_active` (optional boolean)

#### Get user
- `GET /api/v1/users/{user_id}`
- Role: `ADVISOR`

#### Update user
- `PATCH /api/v1/users/{user_id}`
- Role: `ADVISOR`
- Partial update for mutable fields (`full_name`, `phone`, `role`, `email`)

#### Activate user
- `POST /api/v1/users/{user_id}/activate`
- Role: `ADVISOR`

#### Deactivate user
- `POST /api/v1/users/{user_id}/deactivate`
- Role: `ADVISOR`
- Cannot deactivate current authenticated user
- Deactivation also bumps `token_version`

#### Reset password
- `POST /api/v1/users/{user_id}/reset-password`
- Role: `ADVISOR`
- Body:

```json
{
  "new_password": "new-strong-password"
}
```

- Password reset also bumps `token_version`

### Audit log endpoint (advisor-only)

#### List user audit logs
- `GET /api/v1/users/audit-logs`
- Role: `ADVISOR`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)
  - `action` (optional)
  - `target_user_id` (optional)
  - `actor_user_id` (optional)
  - `email` (optional)
  - `from` (optional datetime)
  - `to` (optional datetime)

## Behavior Notes

- Authentication accepts bearer token first; if absent, falls back to `access_token` cookie.
- Token payload validation includes `sub` and `tv` (`token_version`) checks; token/user mismatches return `401`.
- Inactive users cannot authenticate and cannot pass current-user dependency checks.
- `rememberMe` doubles token TTL (`JWT_TTL_HOURS * 2`).
- Password validation requires minimum length of 8 characters.
- Creating/updating with duplicate email raises conflict.
- Attempts to update immutable user fields (`id`, `token_version`, `created_at`, `last_login_at`, `is_active`) are rejected.
- Empty update payloads are rejected.
- Authentication and user-management actions are written to `user_audit_logs`.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `USER.CONFLICT`
- `USER.FORBIDDEN`
- `USER.INVALID_PASSWORD`
- `USER.INVALID_UPDATE`
- `USER.NO_FIELDS_PROVIDED`

Route-level HTTP errors are also used for unauthenticated/forbidden/not-found flows.

## Cross-Domain Integration

- `app/main.py` mounts auth and users routers under `/api/v1`.
- User management authorization is enforced via shared dependency helpers in `app/users/api/deps.py`.
- Global exception envelope from `app/core/exceptions.py` is used for domain-level service errors.

## Tests

Users/auth test suites:
- `tests/auth/api/test_auth.py`
- `tests/auth/api/test_logout_invalidation.py`
- `tests/auth/service/test_jwt_expiration.py`
- `tests/users/api/test_user_management.py`
- `tests/users/api/test_user_reset_password.py`
- `tests/users/api/test_user_token_invalidation.py`
- `tests/users/api/test_user_audit_logs.py`
- `tests/users/services/test_auth_service.py`
- `tests/users/services/test_audit_log_service.py`
- `tests/users/services/test_user_management_policies.py`
- `tests/users/services/test_user_management_service_list_reset.py`
- `tests/users/repository/test_user_repository.py`

Run only this domain:

```bash
pytest tests/auth tests/users -q
```
