from __future__ import annotations

from datetime import date, timedelta
from random import Random

from app.binders.models.binder import BinderStatus
from app.charge.models.charge import ChargeStatus
from app.tax_deadline.models.tax_deadline import TaxDeadlineStatus
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType

from .taxes import DEADLINE_LABELS


def create_reminders(db, rng: Random, businesses, binders, charges, deadlines):
    reminders = []
    today = date.today()
    binders_by_client = {}
    for binder in binders:
        binders_by_client.setdefault(binder.client_id, []).append(binder)
    charges_by_business = {}
    for charge in charges:
        charges_by_business.setdefault(charge.business_id, []).append(charge)
    deadlines_by_business = {}
    for deadline in deadlines:
        deadlines_by_business.setdefault(deadline.business_id, []).append(deadline)

    for business in businesses:
        business_binders = binders_by_client.get(business.client_id, [])
        business_charges = charges_by_business.get(business.id, [])
        business_deadlines = deadlines_by_business.get(business.id, [])

        pending_deadlines = [dl for dl in business_deadlines if dl.status == TaxDeadlineStatus.PENDING]
        if pending_deadlines:
            deadline = rng.choice(pending_deadlines)
            days_before = 7
            send_on = max(today, deadline.due_date - timedelta(days=days_before))
            deadline_label = DEADLINE_LABELS.get(deadline.deadline_type, "מועד מס")
            reminder = Reminder(
                business_id=business.id,
                reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
                status=ReminderStatus.PENDING,
                target_date=deadline.due_date,
                days_before=days_before,
                send_on=send_on,
                tax_deadline_id=deadline.id,
                message=f"תזכורת: מועדי מס מתקרבים ({deadline_label})",
            )
            db.add(reminder)
            reminders.append(reminder)

        idle_binders = [b for b in business_binders if b.status != BinderStatus.RETURNED]
        if idle_binders:
            binder = rng.choice(idle_binders)
            days_idle = max(14, (today - binder.period_start).days)
            reminder = Reminder(
                business_id=business.id,
                reminder_type=ReminderType.BINDER_IDLE,
                status=ReminderStatus.PENDING,
                target_date=today,
                days_before=0,
                send_on=today,
                binder_id=binder.id,
                message=f"תזכורת: תיק {binder.binder_number} לא טופל {days_idle} ימים",
            )
            db.add(reminder)
            reminders.append(reminder)

        unpaid_charges = [
            c
            for c in business_charges
            if c.status == ChargeStatus.ISSUED
            and c.issued_at
            and (today - c.issued_at.date()).days >= 30
        ]
        if unpaid_charges:
            charge = rng.choice(unpaid_charges)
            days_unpaid = (today - charge.issued_at.date()).days
            reminder = Reminder(
                business_id=business.id,
                reminder_type=ReminderType.UNPAID_CHARGE,
                status=ReminderStatus.PENDING,
                target_date=today,
                days_before=0,
                send_on=today,
                charge_id=charge.id,
                message=f"תזכורת: חשבונית #{charge.id} לא שולמה {days_unpaid} ימים",
            )
            db.add(reminder)
            reminders.append(reminder)

    db.flush()
    return reminders
