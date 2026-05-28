## Scope
This file owns only:
- Backend-local implementation details for this documentation area.
- Concrete codebase structure, examples, and conventions subordinate to the canonical YM_Docs rules.

This file must not contain:
- Project-wide architecture rules that override YM_Docs.
- Product/domain behavior.
- Frontend rules.

Source of truth: reference

Canonical project-wide rules:
- `../../../docs/docs/architecture/security.md`
- `../../../docs/docs/architecture/backend.md`

# Auth and Permissions

## Token System

- **Access token**: JWT HS256, short-lived (`AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`, default 15min), sent in `Authorization: Bearer <token>` header.
- **Refresh token**: JWT HS256, longer-lived (`AUTH_REFRESH_TOKEN_EXPIRE_DAYS`, default 7 days), stored in an HttpOnly cookie at path `/api/v1/auth`.
- **Token invalidation**: Every User has a `token_version` integer column. The JWT payload includes `tv` (token version). On `get_current_user`, the server compares `payload["tv"]` against the DB value. `logout_user()` increments `token_version` via `bump_token_version()`, immediately invalidating all outstanding tokens for that user without waiting for JWT expiry.

## Auth Flow

```
POST /api/v1/auth/login
  → AuthService.login(email, password)
      → AuthService.authenticate() — bcrypt verify
      → issue_auth_bundle(user) — generate access + refresh tokens
  → Response: { access_token, user } + Set-Cookie: refresh_token=<token>; HttpOnly

POST /api/v1/auth/refresh
  → AuthService.refresh_access_token(cookie)
      → decode_refresh_token() — verify JWT
      → UserRepository.get_by_id() — validate token_version matches
      → generate_access_token(user)
  → Response: { access_token }

POST /api/v1/auth/logout
  → AuthService.logout_by_refresh_token(cookie)
      → bump_token_version(user_id)
  → Response: 204, clears cookie
```

## get_current_user Dependency

Located at `app/users/api/deps.py`:

```python
def get_current_user(credentials, db) -> AuthSubject:
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(401, "חסר טוקן אימות")

    payload = decode_access_token(token)
    user_id = int(payload["sub"])
    token_version = int(payload["tv"])

    user = UserRepository(db).get_auth_subject_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(401, ...)
    if token_version != user.token_version:
        raise HTTPException(401, ...)

    set_actor_context(user_id=user.id, role=user.role.value)
    return user  # AuthSubject dataclass
```

`AuthSubject` is a lightweight projection with `id`, `full_name`, `email`, `role`, `is_active`, `token_version` — not the full User ORM model.

## Role-Based Access Control

```python
def require_role(*allowed_roles: UserRole):
    def role_checker(current_user: AuthSubject) -> AuthSubject:
        if current_user.role not in allowed_roles:
            raise HTTPException(403, "אין הרשאות מתאימות")
        return current_user
    return role_checker
```

Usage in routers — two patterns:

**Router-level** (applies to all endpoints in the router):
```python
router = APIRouter(
    prefix="/binders",
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
```

**Endpoint-level override** (stricter permission on one endpoint):
```python
@router.delete(
    "/{binder_id}",
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_binder(binder_id: int, db: DBSession, user: CurrentUser):
    ...
```

## Roles

| Role | Access |
|------|--------|
| `ADVISOR` | Full access to all endpoints |
| `SECRETARY` | Operational access; read-oriented; limited write |

Fine-grained checks (e.g. "secretary cannot delete") are implemented with narrower endpoint-level `require_role()` dependencies or service-layer checks.

## Type Aliases (deps.py)

```python
CurrentUser = Annotated[AuthSubject, Depends(get_current_user)]
DBSession   = Annotated[Session, Depends(get_db)]
```

These are the standard injections in route signatures. Using them directly means the JWT and DB are always validated before the route body runs.

## IDOR Prevention

All endpoints that return sensitive data scope queries by `business_id` or `client_record_id` and perform fetch-then-check ownership in the service layer. No endpoint exposes items across business boundaries. This is enforced by convention — new endpoints must follow it.

## Audit Logging

`AuthService` logs every login attempt (success and failure) and every logout via `AuditLogService`. Reason codes for failures: `"user_not_found"`, `"inactive_user"`, `"invalid_password"`. These are stored in the `user_audit_logs` table.
