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
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.guards.client_record_guards import assert_client_record_is_active
from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services.messages import (
    ADVANCE_PAYMENT_NOT_FOUND,
    ADVANCE_PAYMENT_REMINDER_DEFAULT,
    ANNUAL_REPORT_NOT_FOUND,
    ANNUAL_REPORT_REMINDER_DEFAULT,
    BINDER_NOT_FOUND,
    CHARGE_NOT_FOUND,
    CHARGE_SCOPE_MISMATCH,
    CLIENT_NOT_FOUND,
    CUSTOM_REMINDER_MESSAGE_REQUIRED,
    DOCUMENT_MISSING_MESSAGE_REQUIRED,
    IDLE_BINDER_REMINDER_DEFAULT,
    NEGATIVE_DAYS,
    TAX_DEADLINE_NOT_FOUND,
    TAX_DEADLINE_REMINDER_DEFAULT,
    UNPAID_CHARGE_REMINDER_DEFAULT,
    VAT_FILING_REMINDER_DEFAULT,
)
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def _require_non_negative_days(days_before: int) -> None:
    if days_before < 0:
        raise AppError(NEGATIVE_DAYS, "REMINDER.NEGATIVE_DAYS")


def _resolve_client_record_id(client_id: int, repo: ClientRecordRepository) -> int:
    client_record = repo.get_by_client_id(client_id)
    assert_client_record_is_active(client_record)
    return client_record.id


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
        raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "REMINDER.CLIENT_NOT_FOUND")
    if not tax_deadline_repo.get_by_id(tax_deadline_id):
        raise NotFoundError(TAX_DEADLINE_NOT_FOUND.format(tax_deadline_id=tax_deadline_id), "REMINDER.NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = TAX_DEADLINE_REMINDER_DEFAULT.format(days_before=days_before, target_date=target_date)
    client_record_id = _resolve_client_record_id(client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=client_id,
        client_record_id=client_record_id,
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
        raise NotFoundError(TAX_DEADLINE_NOT_FOUND.format(tax_deadline_id=tax_deadline_id), "REMINDER.NOT_FOUND")
    if not client_repo.get_by_id(deadline.client_id):
        raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=deadline.client_id), "REMINDER.CLIENT_NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = VAT_FILING_REMINDER_DEFAULT.format(days_before=days_before, target_date=target_date)
    client_record_id = _resolve_client_record_id(deadline.client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=deadline.client_id,
        client_record_id=client_record_id,
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
        raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "REMINDER.NOT_FOUND")
    if not client_repo.get_by_id(binder.client_id):
        raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=binder.client_id), "REMINDER.CLIENT_NOT_FOUND")
    _require_non_negative_days(days_idle)

    target_date = date.today() + timedelta(days=days_idle)
    send_on = date.today()
    if message is None:
        message = IDLE_BINDER_REMINDER_DEFAULT.format(days_idle=days_idle)
    client_record_id = _resolve_client_record_id(binder.client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=binder.client_id,
        client_record_id=client_record_id,
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
        raise NotFoundError(ANNUAL_REPORT_NOT_FOUND.format(annual_report_id=annual_report_id), "REMINDER.NOT_FOUND")
    if not client_repo.get_by_id(report.client_id):
        raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=report.client_id), "REMINDER.CLIENT_NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = ANNUAL_REPORT_REMINDER_DEFAULT.format(days_before=days_before, target_date=target_date)
    client_record_id = _resolve_client_record_id(report.client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=report.client_id,
        client_record_id=client_record_id,
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
        raise NotFoundError(CHARGE_NOT_FOUND.format(charge_id=charge_id), "REMINDER.NOT_FOUND")
    if charge.client_id != client_id or charge.business_id != business_id:
        raise AppError(CHARGE_SCOPE_MISMATCH, "REMINDER.CHARGE_SCOPE_MISMATCH")
    _require_non_negative_days(days_unpaid)

    target_date = date.today()
    send_on = date.today()
    if message is None:
        message = UNPAID_CHARGE_REMINDER_DEFAULT.format(days_unpaid=days_unpaid)
    client_record_id = _resolve_client_record_id(client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=client_id,
        client_record_id=client_record_id,
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
        raise NotFoundError(ADVANCE_PAYMENT_NOT_FOUND.format(advance_payment_id=advance_payment_id), "REMINDER.NOT_FOUND")
    _require_non_negative_days(days_before)

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = ADVANCE_PAYMENT_REMINDER_DEFAULT.format(days_before=days_before, target_date=target_date)
    client_record_id = _resolve_client_record_id(business.client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=business.client_id,
        client_record_id=client_record_id,
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
        raise AppError(DOCUMENT_MISSING_MESSAGE_REQUIRED, "REMINDER.MESSAGE_REQUIRED")

    send_on = target_date - timedelta(days=days_before)
    client_record_id = _resolve_client_record_id(business.client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=business.client_id,
        client_record_id=client_record_id,
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
        raise AppError(CUSTOM_REMINDER_MESSAGE_REQUIRED, "REMINDER.MESSAGE_REQUIRED")

    send_on = target_date - timedelta(days=days_before)
    client_record_id = _resolve_client_record_id(business.client_id, ClientRecordRepository(reminder_repo.db))

    return reminder_repo.create(
        client_id=business.client_id,
        client_record_id=client_record_id,
        business_id=business_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )
