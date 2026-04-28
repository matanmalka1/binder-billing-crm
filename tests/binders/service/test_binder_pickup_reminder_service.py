from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.binders.models.binder import BinderStatus
from app.binders.services.binder_pickup_reminder_service import BinderPickupReminderService
from app.core.exceptions import AppError, NotFoundError


def _service(monkeypatch, binder, last=None):
    sent = {}
    monkeypatch.setattr(
        "app.binders.services.binder_pickup_reminder_service.BinderRepository",
        lambda db: SimpleNamespace(get_by_id=lambda binder_id: binder),
    )
    monkeypatch.setattr(
        "app.binders.services.binder_pickup_reminder_service.NotificationRepository",
        lambda db: SimpleNamespace(get_last_for_binder_trigger=lambda *_: last),
    )
    monkeypatch.setattr(
        "app.binders.services.binder_pickup_reminder_service.NotificationService",
        lambda db: SimpleNamespace(notify_pickup_reminder=lambda **kwargs: sent.update(kwargs) or True),
    )
    return BinderPickupReminderService(SimpleNamespace()), sent


def test_send_pickup_reminder_sends_for_ready_binder(monkeypatch):
    binder = SimpleNamespace(id=7, status=BinderStatus.READY_FOR_PICKUP, client_record_id=3)
    service, sent = _service(monkeypatch, binder)

    service.send_pickup_reminder(binder_id=7, triggered_by=11)

    assert sent["binder"] is binder
    assert sent["client_record_id"] == 3
    assert sent["triggered_by"] == 11


def test_send_pickup_reminder_rejects_missing_binder(monkeypatch):
    service, _ = _service(monkeypatch, binder=None)

    with pytest.raises(NotFoundError) as exc:
        service.send_pickup_reminder(binder_id=404, triggered_by=1)

    assert exc.value.code == "BINDER.NOT_FOUND"


def test_send_pickup_reminder_enforces_cooldown(monkeypatch):
    binder = SimpleNamespace(id=8, status=BinderStatus.READY_FOR_PICKUP, client_record_id=4)
    last = SimpleNamespace(created_at=datetime.now(timezone.utc) - timedelta(days=2))
    service, _ = _service(monkeypatch, binder, last=last)

    with pytest.raises(AppError) as exc:
        service.send_pickup_reminder(binder_id=8, triggered_by=1)

    assert exc.value.code == "BINDER.REMINDER_TOO_SOON"
