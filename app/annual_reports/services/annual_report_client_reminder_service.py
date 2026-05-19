"""Sends a follow-up reminder to client when annual report is stuck in PENDING_CLIENT."""

from __future__ import annotations

import datetime as _dt

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.repositories.annual_report_repository import (
    AnnualReportRepository,
)
from app.annual_reports.services.messages import ANNUAL_REPORT_NOT_FOUND
from app.core.exceptions import AppError, NotFoundError
from app.notification.models.notification import NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.constants import ANNUAL_REMINDER_COOLDOWN_DAYS
from app.notification.services.notification_service import NotificationService


class AnnualReportClientReminderService:
    def __init__(self, db: Session):
        self.report_repo = AnnualReportRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.notification_service = NotificationService(db)

    def send_client_reminder(self, report_id: int, triggered_by: int) -> None:
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(
                ANNUAL_REPORT_NOT_FOUND.format(report_id=report_id),
                "ANNUAL_REPORT.NOT_FOUND",
            )

        if report.status != AnnualReportStatus.PENDING_CLIENT:
            raise AppError(
                "הדוח אינו במצב ממתין לאישור לקוח",
                "ANNUAL_REPORT.NOT_PENDING_CLIENT",
            )

        last = self.notification_repo.get_last_for_annual_report_trigger(
            report_id, NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER
        )
        if last:
            days_since = (
                _dt.datetime.now(_dt.UTC) - last.created_at.replace(tzinfo=_dt.UTC)
            ).days
            if days_since < ANNUAL_REMINDER_COOLDOWN_DAYS:
                raise AppError(
                    f"תזכורת נשלחה לפני {days_since} ימים. ניתן לשלוח שוב לאחר {ANNUAL_REMINDER_COOLDOWN_DAYS} ימים.",
                    "ANNUAL_REPORT.REMINDER_TOO_SOON",
                )

        self.notification_service.notify_client(
            client_record_id=report.client_record_id,
            trigger=NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER,
            template_data={"tax_year": report.tax_year},
            annual_report_id=report.id,
            triggered_by=triggered_by,
        )
