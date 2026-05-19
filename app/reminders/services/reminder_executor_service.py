from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.reminders.models.reminder import (
    Reminder,
    ReminderActionType,
    ReminderStatus,
)
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time_utils import utcnow


@dataclass(frozen=True)
class ReminderExecutionResult:
    processed: int
    fired: int
    failed: int


class ReminderExecutorService:
    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)

    def fire_due(self, *, now: datetime | None = None, limit: int = 100) -> ReminderExecutionResult:
        now = now or utcnow()
        reminders = self.reminder_repo.list_due_scheduled(now, limit=limit)
        fired = 0
        failed = 0
        for reminder in reminders:
            if self._execute(reminder, now):
                fired += 1
            else:
                failed += 1
        return ReminderExecutionResult(
            processed=len(reminders),
            fired=fired,
            failed=failed,
        )

    def _execute(self, reminder: Reminder, now: datetime) -> bool:
        reason = self._unsupported_reason(reminder.action_type)
        self.reminder_repo.update_status(
            reminder.id,
            ReminderStatus.FAILED,
            fired_at=now,
            failure_reason=reason,
        )
        return False

    def _unsupported_reason(self, action_type: ReminderActionType) -> str:
        if action_type == ReminderActionType.CREATE_TASK:
            return "ביצוע CREATE_TASK עדיין לא ממומש: ממתין למודל Task persisted"
        if action_type == ReminderActionType.CREATE_TASK_AND_NOTIFY:
            return "ביצוע CREATE_TASK_AND_NOTIFY עדיין לא ממומש: ממתין ל-Task ולתזמור פעולות"
        return "ביצוע SEND_NOTIFICATION עדיין לא ממומש: ממתין לחיבור NotificationService נקי"
