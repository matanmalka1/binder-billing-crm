from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.services.annual_report_client_reminder_service import (
    AnnualReportClientReminderService,
)
from app.core.exceptions import AppError, NotFoundError


def _service(monkeypatch, report, last=None):
    sent = {}
    monkeypatch.setattr(
        "app.annual_reports.services.annual_report_client_reminder_service.AnnualReportRepository",
        lambda db: SimpleNamespace(get_by_id=lambda report_id: report),
    )
    monkeypatch.setattr(
        "app.annual_reports.services.annual_report_client_reminder_service.NotificationRepository",
        lambda db: SimpleNamespace(get_last_for_annual_report_trigger=lambda *_: last),
    )
    monkeypatch.setattr(
        "app.annual_reports.services.annual_report_client_reminder_service.NotificationService",
        lambda db: SimpleNamespace(
            notify_annual_report_client_reminder=lambda **kwargs: sent.update(kwargs) or True,
        ),
    )
    return AnnualReportClientReminderService(SimpleNamespace()), sent


def test_send_client_reminder_sends_for_pending_client_report(monkeypatch):
    report = SimpleNamespace(
        id=5,
        client_record_id=9,
        tax_year=2025,
        status=AnnualReportStatus.PENDING_CLIENT,
    )
    service, sent = _service(monkeypatch, report)

    service.send_client_reminder(report_id=5, triggered_by=17)

    assert sent == {
        "client_record_id": 9,
        "annual_report_id": 5,
        "tax_year": 2025,
        "triggered_by": 17,
    }


def test_send_client_reminder_rejects_missing_report(monkeypatch):
    service, _ = _service(monkeypatch, report=None)

    with pytest.raises(NotFoundError) as exc:
        service.send_client_reminder(report_id=404, triggered_by=1)

    assert exc.value.code == "ANNUAL_REPORT.NOT_FOUND"


def test_send_client_reminder_enforces_cooldown(monkeypatch):
    report = SimpleNamespace(id=6, status=AnnualReportStatus.PENDING_CLIENT)
    last = SimpleNamespace(created_at=datetime.now(timezone.utc) - timedelta(days=1))
    service, _ = _service(monkeypatch, report, last=last)

    with pytest.raises(AppError) as exc:
        service.send_client_reminder(report_id=6, triggered_by=1)

    assert exc.value.code == "ANNUAL_REPORT.REMINDER_TOO_SOON"
