"""reminder_factory.py

Single module for all reminder creation flows.
Replaces the old factory.py + factory_extended.py split (which had no principled boundary).

Ownership rule enforced here:
  client_id is ALWAYS set — it is the primary anchor (legal entity).
  business_id is set ADDITIONALLY when the reminder is scoped to a specific business.
  The repository no longer enforces XOR; it requires client_id unconditionally.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository as AnnualReportRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import get_business_or_raise
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def _require_non_negative_days(days_before: int) -> None:
    if days_before < 0:
        raise AppError("המספר המייצג כמה ימים לפני חייב להיות מספר לא שלילי", "REMINDER.NEGATIVE_DAYS")


# ── Client-scoped reminders ───────────────────────────────────────────────────
# client_id comes directly from the caller or is resolved from a linked entity.
# business_id is not set — these are legal-entity level events.

def create_tax_deadline_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    tax_deadline_repo: TaxDeadlineRepository,
    *,
    client_id: int,
    tax_deadline_id: int,
    target_date: date,
    days_before: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    if not client_repo.get_by_id(client_id):
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "REMINDER.CLIENT_NOT_FOUND")
    if not tax_deadline_repo.get_by_id(tax_deadline_id):
        raise NotFoundError(f"מועד מס {tax_deadline_id} לא נמצא", "REMINDER.NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = f"תזכורת: מועד מס בעוד {days_before} ימים ({target_date})"

    return reminder_repo.create(
        client_id=client_id,
        reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message,
        tax_deadline_id=tax_deadline_id,
        created_by=created_by,
    )


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


def create_idle_binder_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    binder_repo: BinderRepository,
    *,
    binder_id: int,
    days_idle: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    binder = binder_repo.get_by_id(binder_id)
    if not binder:
        raise NotFoundError(f"תיק {binder_id} לא נמצא", "REMINDER.NOT_FOUND")
    if not client_repo.get_by_id(binder.client_id):
        raise NotFoundError(f"לקוח {binder.client_id} לא נמצא", "REMINDER.CLIENT_NOT_FOUND")
    _require_non_negative_days(days_idle)

    target_date = date.today() + timedelta(days=days_idle)
    send_on = date.today()
    if message is None:
        message = f"תזכורת: תיק לא טופל {days_idle} ימים"

    return reminder_repo.create(
        client_id=binder.client_id,
        reminder_type=ReminderType.BINDER_IDLE,
        target_date=target_date,
        days_before=0,
        send_on=send_on,
        message=message,
        binder_id=binder_id,
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


# ── Business-scoped reminders ─────────────────────────────────────────────────
# client_id is resolved from business.client_id so both anchors are always set.

def create_unpaid_charge_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    charge_repo: ChargeRepository,
    *,
    client_id: int,
    business_id: Optional[int] = None,
    charge_id: int,
    days_unpaid: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    if business_id is not None:
        get_business_or_raise(business_repo.db, business_id)
    charge = charge_repo.get_by_id(charge_id)
    if not charge:
        raise NotFoundError(f"חיוב {charge_id} לא נמצא", "REMINDER.NOT_FOUND")
    if charge.client_id != client_id or charge.business_id != business_id:
        raise AppError("החיוב לא תואם להקשר שנשלח", "REMINDER.CHARGE_SCOPE_MISMATCH")
    _require_non_negative_days(days_unpaid)

    target_date = date.today()
    send_on = date.today()
    if message is None:
        message = f"תזכורת: חשבונית לא שולמה {days_unpaid} ימים"

    return reminder_repo.create(
        client_id=client_id,
        business_id=business_id,          # optional context; client_id always set above
        reminder_type=ReminderType.UNPAID_CHARGE,
        target_date=target_date,
        days_before=0,
        send_on=send_on,
        message=message,
        charge_id=charge_id,
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
    business = get_business_or_raise(business_repo.db, business_id)
    if not advance_payment_repo.get_by_id(advance_payment_id):
        raise NotFoundError(f"מקדמה {advance_payment_id} לא נמצאה", "REMINDER.NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = f"תזכורת: מועד תשלום מקדמה בעוד {days_before} ימים ({target_date})"

    return reminder_repo.create(
        client_id=business.client_id,     # resolved from business — always set
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
    business = get_business_or_raise(business_repo.db, business_id)
    _require_non_negative_days(days_before)
    if not message or not message.strip():
        raise AppError("נדרש טקסט עבור תזכורת מסמך חסר", "REMINDER.MESSAGE_REQUIRED")

    send_on = target_date - timedelta(days=days_before)

    return reminder_repo.create(
        client_id=business.client_id,     # resolved from business — always set
        business_id=business_id,
        reminder_type=ReminderType.DOCUMENT_MISSING,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )


def create_custom_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    business_id: int,
    target_date: date,
    days_before: int,
    message: str,
    created_by: Optional[int] = None,
) -> Reminder:
    business = get_business_or_raise(business_repo.db, business_id)
    _require_non_negative_days(days_before)
    if not message or not message.strip():
        raise AppError("נדרש טקסט עבור תזכורות מותאמות אישית", "REMINDER.MESSAGE_REQUIRED")

    send_on = target_date - timedelta(days=days_before)

    return reminder_repo.create(
        client_id=business.client_id,     # resolved from business — always set
        business_id=business_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )