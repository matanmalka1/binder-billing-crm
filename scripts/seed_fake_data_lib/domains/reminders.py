from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from random import Random

from app.binders.models.binder import BinderStatus
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType


def create_reminders(db, rng: Random, businesses, binders, charges, deadlines):
    reminders = []
    active_identities: set[tuple[int, ReminderType, date]] = set()
    today = date.today()
    binders_by_client = {}
    for binder in binders:
        binders_by_client.setdefault(binder.client_id, []).append(binder)

    for business in businesses:
        business_binders = binders_by_client.get(business.client_id, [])

        idle_binders = [b for b in business_binders if b.status != BinderStatus.RETURNED]
        if idle_binders:
            binder = rng.choice(idle_binders)
            days_idle = max(14, (today - binder.period_start).days)
            reminder = Reminder(
                client_record_id=business.client_id,
                business_id=business.id,
                reminder_type=ReminderType.BINDER_IDLE,
                status=ReminderStatus.PENDING,
                target_date=today,
                days_before=0,
                send_on=today,
                binder_id=binder.id,
                message=f"תזכורת: תיק {binder.binder_number} לא טופל {days_idle} ימים",
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
            )
            _add_unique_active_reminder(db, reminders, active_identities, reminder)

        missing_doc_date = today + timedelta(days=rng.randint(3, 21))
        document_reminder = Reminder(
            client_record_id=business.client_id,
            business_id=business.id,
            reminder_type=ReminderType.DOCUMENT_MISSING,
            status=ReminderStatus.PENDING,
            target_date=missing_doc_date,
            days_before=3,
            send_on=missing_doc_date - timedelta(days=3),
            message="תזכורת: חסרים מסמכים להשלמת הטיפול",
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
        )
        _add_unique_active_reminder(db, reminders, active_identities, document_reminder)

        custom_date = today + timedelta(days=rng.randint(7, 35))
        reminder = Reminder(
            client_record_id=business.client_id,
            business_id=business.id,
            reminder_type=ReminderType.CUSTOM,
            status=ReminderStatus.PENDING,
            target_date=custom_date,
            days_before=2,
            send_on=custom_date - timedelta(days=2),
            message="תזכורת פנימית: לבצע שיחת מעקב עם הלקוח",
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
        )
        _add_unique_active_reminder(db, reminders, active_identities, reminder)

    db.flush()


def _add_unique_active_reminder(db, reminders, active_identities, reminder: Reminder) -> None:
    identity = (
        reminder.client_record_id,
        reminder.reminder_type,
        reminder.target_date,
    )
    if identity in active_identities:
        return
    active_identities.add(identity)
    db.add(reminder)
    reminders.append(reminder)
