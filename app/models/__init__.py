from __future__ import annotations

from importlib import import_module
from typing import Final

_EXPORTS: Final[dict[str, str]] = {
    # Sprint 1–2 (core)
    "User": "app.models.user",
    "UserRole": "app.models.user",
    "Client": "app.models.client",
    "ClientType": "app.models.client",
    "ClientStatus": "app.models.client",
    "Binder": "app.models.binder",
    "BinderStatus": "app.models.binder",
    "BinderStatusLog": "app.models.binder_status_log",
    # Sprint 3–4 (alembic-managed tables)
    "Charge": "app.models.charge",
    "ChargeType": "app.models.charge",
    "ChargeStatus": "app.models.charge",
    "Invoice": "app.models.invoice",
    "Notification": "app.models.notification",
    "NotificationChannel": "app.models.notification",
    "NotificationStatus": "app.models.notification",
    "NotificationTrigger": "app.models.notification",
    "PermanentDocument": "app.models.permanent_document",
    "DocumentType": "app.models.permanent_document",
}

__all__ = sorted(_EXPORTS.keys())


def __getattr__(name: str):
    module_path = _EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_path)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
