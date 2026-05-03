from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from random import Random

from app.binders.models.binder import BinderStatus
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType


def _add_unique(db, reminders, active_identities: set, reminder: Reminder) -> None:
    identity = (reminder.client_record_id, reminder.reminder_type, reminder.target_date)
    if identity in active_identities:
        return
    active_identities.add(identity)
    db.add(reminder)
    reminders.append(reminder)


def create_reminders(db, rng: Random, businesses, binders, charges, deadlines) -> None:
    active_identities: set[tuple[int, ReminderType, date]] = set()
    reminders: list[Reminder] = []
    today = date.today()

    binders_by_client: dict[int, list] = {}
    for binder in binders:
        binders_by_client.setdefault(binder.client_id, []).append(binder)

    # Build deadline lookup for linked reminders
    deadlines_by_client: dict[int, list] = {}
    for dl in deadlines:
        deadlines_by_client.setdefault(dl.client_record_id, []).append(dl)

    for business in businesses:
        business_binders = binders_by_client.get(business.client_id, [])
        idle_binders = [b for b in business_binders if b.status != BinderStatus.RETURNED]
        if idle_binders:
            binder = rng.choice(idle_binders)
            days_idle = max(14, (today - binder.period_start).days) if binder.period_start else 14
            _add_unique(db, reminders, active_identities, Reminder(
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
            ))

        missing_doc_date = today + timedelta(days=rng.randint(3, 21))
        _add_unique(db, reminders, active_identities, Reminder(
            client_record_id=business.client_id,
            business_id=business.id,
            reminder_type=ReminderType.DOCUMENT_MISSING,
            status=ReminderStatus.PENDING,
            target_date=missing_doc_date,
            days_before=3,
            send_on=missing_doc_date - timedelta(days=3),
            message="תזכורת: חסרים מסמכים להשלמת הטיפול",
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
        ))

        # Linked deadline reminder (when a pending deadline exists)
        client_deadlines = [
            dl for dl in deadlines_by_client.get(business.client_id, [])
            if hasattr(dl, "status") and dl.status and dl.status.value == "pending"
        ]
        if client_deadlines:
            dl = rng.choice(client_deadlines)
            target_date = dl.due_date + timedelta(days=rng.randint(-7, 7))
            if target_date >= today:
                _add_unique(db, reminders, active_identities, Reminder(
                    client_record_id=business.client_id,
                    business_id=business.id,
                    reminder_type=ReminderType.CUSTOM,
                    status=ReminderStatus.PENDING,
                    target_date=target_date,
                    days_before=2,
                    send_on=max(today, target_date - timedelta(days=2)),
                    message=f"תזכורת פנימית: מועד מס {dl.due_date} - לבצע מעקב עם הלקוח",
                    created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
                ))

    db.flush()
