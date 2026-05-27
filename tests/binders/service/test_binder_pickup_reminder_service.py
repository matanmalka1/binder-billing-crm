from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.binders.models.binder import BinderLocationStatus
from app.binders.services.binder_handover_reminder_service import (
    BinderHandoverReminderService,
)
from app.core.exceptions import AppError, NotFoundError


def _service(monkeypatch, binder, last=None):
    sent = {}
    monkeypatch.setattr(
        "app.binders.services.binder_handover_reminder_service.BinderRepository",
        lambda db: SimpleNamespace(get_by_id=lambda binder_id: binder),
    )
    monkeypatch.setattr(
        "app.binders.services.binder_handover_reminder_service.NotificationRepository",
        lambda db: SimpleNamespace(get_last_for_binder_trigger=lambda *_: last),
    )
    monkeypatch.setattr(
        "app.binders.services.binder_handover_reminder_service.NotificationService",
        lambda db: SimpleNamespace(notify_client=lambda **kwargs: sent.update(kwargs) or True),
    )
    return BinderHandoverReminderService(SimpleNamespace()), sent


def test_send_handover_reminder_sends_for_ready_binder(monkeypatch):
    binder = SimpleNamespace(
        id=7,
        location_status=BinderLocationStatus.READY_FOR_HANDOVER,
        client_record_id=3,
        binder_number="BN-7",
    )
    service, sent = _service(monkeypatch, binder)

    service.send_handover_reminder(binder_id=7, triggered_by=11)

    assert sent["client_record_id"] == 3
    assert sent["binder_id"] == 7
    assert sent["triggered_by"] == 11
    assert sent["template_data"]["binder_number"] == "BN-7"


def test_send_handover_reminder_rejects_missing_binder(monkeypatch):
    service, _ = _service(monkeypatch, binder=None)

    with pytest.raises(NotFoundError) as exc:
        service.send_handover_reminder(binder_id=404, triggered_by=1)

    assert exc.value.code == "BINDER.NOT_FOUND"


def test_send_handover_reminder_enforces_cooldown(monkeypatch):
    binder = SimpleNamespace(
        id=8,
        location_status=BinderLocationStatus.READY_FOR_HANDOVER,
        client_record_id=4,
    )
    last = SimpleNamespace(created_at=datetime.now(UTC) - timedelta(days=2))
    service, _ = _service(monkeypatch, binder, last=last)

    with pytest.raises(AppError) as exc:
        service.send_handover_reminder(binder_id=8, triggered_by=1)

    assert exc.value.code == "BINDER.REMINDER_TOO_SOON"
