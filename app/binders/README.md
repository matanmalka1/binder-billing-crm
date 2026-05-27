# Binders Domain

Manages physical binder intake, office lifecycle, handover, history, and list views.

## Lifecycle Model

Binder lifecycle is split into two fields:

- `location_status`: `in_office`, `ready_for_handover`, `handed_over`
- `capacity_status`: `open`, `full`

Only `location_status=in_office` and `capacity_status=open` is eligible for material intake.
All lifecycle and capacity transitions go through `BinderLifecycleService`.

## Audit

Lifecycle changes are recorded in `BinderLifecycleLog` using one row per changed field:

- `field_name`
- `old_value`
- `new_value`
- `changed_by_user_id`
- `changed_at`
- `notes`

## API

Lifecycle endpoints:

- `POST /api/v1/binders/{binder_id}/receive-material`
- `POST /api/v1/binders/{binder_id}/mark-full`
- `POST /api/v1/binders/{binder_id}/reopen-capacity`
- `POST /api/v1/binders/{binder_id}/mark-ready-for-handover`
- `POST /api/v1/binders/{binder_id}/revert-ready-for-handover`
- `POST /api/v1/binders/{binder_id}/handover-to-client`

List filters use `location_status` and `capacity_status`.
Responses return lifecycle values only; UI labels live in the frontend.
