from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.clients.enums import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.notification.models.notification import NotificationStatus, NotificationTrigger

# Triggers allowed even for FROZEN/CLOSED clients
_FROZEN_CLOSED_ALLOWED = {
    NotificationTrigger.CLIENT_MISSING_INFORMATION,
    NotificationTrigger.CLIENT_DOCUMENTS_REQUEST,
}

from app.annual_reports.models.annual_report_enums import AnnualReportStatus as _ARS

_ANNUAL_REPORT_DOCUMENTS_REQUEST_ALLOWED_STATUSES = frozenset({
    _ARS.NOT_STARTED,
    _ARS.COLLECTING_DOCS,
    _ARS.IN_PREPARATION,
})

ANNUAL_REMINDER_COOLDOWN_DAYS = 2


@dataclass
class PolicyResult:
    blocked: bool
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)


class NotificationPolicyService:
    """
    Business rule gate for sending notifications.

    Contract:
    - blocked=True → caller returns NotificationResult(status=blocked), saves NO record.
    - blocked=False with warnings → caller proceeds, includes warnings in response.
    - Missing Person/email is NOT policy. Handled by contact resolver → produces skipped.
    """

    def can_send(
        self,
        client_record: ClientRecord,
        trigger: NotificationTrigger,
        *,
        db: Session | None = None,
        entity_id: int | None = None,
        annual_report_id: int | None = None,
    ) -> PolicyResult:
        status = client_record.status

        if status in (ClientStatus.FROZEN, ClientStatus.CLOSED):
            if trigger not in _FROZEN_CLOSED_ALLOWED:
                return PolicyResult(
                    blocked=True,
                    reason="לא ניתן לשלוח הודעות ללקוח שהסטטוס שלו הוא מוקפא או סגור",
                )

        # Binder-specific: validate location_status == READY_FOR_HANDOVER
        if trigger == NotificationTrigger.BINDER_READY_FOR_HANDOVER:
            if db is None or entity_id is None:
                return PolicyResult(blocked=True, reason="חסר מזהה קלסר לאימות")
            result = self._check_binder_ready_for_handover(db, entity_id)
            if result is not None:
                return result

        # Annual report triggers
        client_record_id = client_record.id
        if trigger == NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER:
            if db is None or annual_report_id is None:
                return PolicyResult(blocked=True, reason="חסר מזהה דוח שנתי לאימות")
            result = self._check_annual_report_client_reminder(
                db, annual_report_id, client_record_id=client_record_id
            )
            if result is not None:
                return result

        if trigger == NotificationTrigger.ANNUAL_REPORT_DOCUMENTS_REQUEST:
            if db is None or annual_report_id is None:
                return PolicyResult(blocked=True, reason="חסר מזהה דוח שנתי לאימות")
            result = self._check_annual_report_documents_request(
                db, annual_report_id, client_record_id=client_record_id
            )
            if result is not None:
                return result

        return PolicyResult(blocked=False)

    def _check_binder_ready_for_handover(
        self, db: Session, binder_id: int
    ) -> PolicyResult | None:
        from app.binders.models.binder import Binder, BinderLocationStatus

        binder = db.get(Binder, binder_id)
        if binder is None or binder.location_status != BinderLocationStatus.READY_FOR_HANDOVER:
            return PolicyResult(
                blocked=True,
                reason="הקלסר אינו במצב מוכן למסירה",
            )
        return None

    def _check_annual_report_client_reminder(
        self, db: Session, annual_report_id: int, client_record_id: int | None = None
    ) -> PolicyResult | None:
        from app.annual_reports.models.annual_report_enums import AnnualReportStatus
        from app.annual_reports.models.annual_report_model import AnnualReport
        from app.notification.repositories.notification_repository import NotificationRepository

        report = db.get(AnnualReport, annual_report_id)
        if report is None:
            return PolicyResult(blocked=True, reason="הדוח השנתי לא נמצא")
        if client_record_id is not None and report.client_record_id != client_record_id:
            return PolicyResult(blocked=True, reason="הדוח השנתי לא שייך ללקוח זה")
        if report.status != AnnualReportStatus.PENDING_CLIENT:
            return PolicyResult(
                blocked=True,
                reason="הדוח אינו במצב ממתין לאישור לקוח",
            )

        repo = NotificationRepository(db)
        last = repo.get_last_for_annual_report_trigger(
            annual_report_id, NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER
        )
        if last and last.status == NotificationStatus.SENT:
            days_since = (_dt.datetime.now(_dt.UTC) - last.created_at.replace(tzinfo=_dt.UTC)).days
            if days_since < ANNUAL_REMINDER_COOLDOWN_DAYS:
                return PolicyResult(
                    blocked=True,
                    reason=(
                        f"תזכורת נשלחה לפני {days_since} ימים. "
                        f"ניתן לשלוח שוב לאחר {ANNUAL_REMINDER_COOLDOWN_DAYS} ימים."
                    ),
                )
        return None

    def _check_annual_report_documents_request(
        self, db: Session, annual_report_id: int, client_record_id: int | None = None
    ) -> PolicyResult | None:
        from app.annual_reports.models.annual_report_model import AnnualReport

        report = db.get(AnnualReport, annual_report_id)
        if report is None:
            return PolicyResult(blocked=True, reason="הדוח השנתי לא נמצא")
        if client_record_id is not None and report.client_record_id != client_record_id:
            return PolicyResult(blocked=True, reason="הדוח השנתי לא שייך ללקוח זה")
        if report.status not in _ANNUAL_REPORT_DOCUMENTS_REQUEST_ALLOWED_STATUSES:
            return PolicyResult(
                blocked=True,
                reason="הדוח אינו במצב המאפשר שליחת בקשת מסמכים",
            )
        return None
