from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository as AnnualReportRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services.factory import _require_non_negative_days
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def create_vat_filing_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    tax_deadline_repo: TaxDeadlineRepository,
    *,
    tax_deadline_id: int,
    target_date: date,
    days_before: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    deadline = tax_deadline_repo.get_by_id(tax_deadline_id)
    if not deadline:
        raise NotFoundError(f"מועד מס {tax_deadline_id} לא נמצא", "REMINDER.NOT_FOUND")
    if not client_repo.get_by_id(deadline.client_id):
        raise NotFoundError(f"לקוח {deadline.client_id} לא נמצא", "REMINDER.CLIENT_NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = f"תזכורת: מועד הגשת דוח מע\"מ בעוד {days_before} ימים ({target_date})"

    return reminder_repo.create(
        client_id=deadline.client_id,
        reminder_type=ReminderType.VAT_FILING,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message,
        tax_deadline_id=tax_deadline_id,
        created_by=created_by,
    )


def create_annual_report_deadline_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    annual_report_repo: AnnualReportRepository,
    *,
    annual_report_id: int,
    target_date: date,
    days_before: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    report = annual_report_repo.get_by_id(annual_report_id)
    if not report:
        raise NotFoundError(f"דוח שנתי {annual_report_id} לא נמצא", "REMINDER.NOT_FOUND")
    if not client_repo.get_by_id(report.client_id):
        raise NotFoundError(f"לקוח {report.client_id} לא נמצא", "REMINDER.CLIENT_NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = f"תזכורת: מועד הגשת הדוח השנתי בעוד {days_before} ימים ({target_date})"

    return reminder_repo.create(
        client_id=report.client_id,
        reminder_type=ReminderType.ANNUAL_REPORT_DEADLINE,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message,
        annual_report_id=annual_report_id,
        created_by=created_by,
    )


def create_advance_payment_due_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    advance_payment_repo: AdvancePaymentRepository,
    *,
    business_id: int,
    advance_payment_id: int,
    target_date: date,
    days_before: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    get_business_or_raise(business_repo.db, business_id)
    if not advance_payment_repo.get_by_id(advance_payment_id):
        raise NotFoundError(f"מקדמה {advance_payment_id} לא נמצאה", "REMINDER.NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = f"תזכורת: מועד תשלום מקדמה בעוד {days_before} ימים ({target_date})"

    return reminder_repo.create(
        business_id=business_id,
        reminder_type=ReminderType.ADVANCE_PAYMENT_DUE,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message,
        advance_payment_id=advance_payment_id,
        created_by=created_by,
    )


def create_document_missing_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    business_id: int,
    target_date: date,
    days_before: int,
    message: str,
    created_by: Optional[int] = None,
) -> Reminder:
    get_business_or_raise(business_repo.db, business_id)
    _require_non_negative_days(days_before)
    if not message or not message.strip():
        raise AppError("נדרש טקסט עבור תזכורת מסמך חסר", "REMINDER.MESSAGE_REQUIRED")

    send_on = target_date - timedelta(days=days_before)

    return reminder_repo.create(
        business_id=business_id,
        reminder_type=ReminderType.DOCUMENT_MISSING,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )
