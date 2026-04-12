from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.notification.models.notification import (
    Notification,
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from app.utils.time_utils import utcnow


class NotificationRepository:
    """Data access layer for Notification entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,                                          # PRIMARY anchor — always required
        trigger: NotificationTrigger,
        channel: NotificationChannel,
        recipient: str,
        content_snapshot: str,
        business_id: Optional[int] = None,                      # OPTIONAL context
        binder_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> Notification:
        if client_id is None:
            raise AppError(
                "התראה חייבת לשייך ללקוח",
                "NOTIFICATION.MISSING_CLIENT",
            )
        notification = Notification(
            client_id=client_id,
            business_id=business_id,
            binder_id=binder_id,
            trigger=trigger,
            channel=channel,
            recipient=recipient,
            content_snapshot=content_snapshot,
            status=NotificationStatus.PENDING,
            severity=severity,
            triggered_by=triggered_by,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_sent(self, notification_id: int) -> Optional[Notification]:
        notification = self.get_by_id(notification_id)
        if not notification:
            return None
        notification.status = NotificationStatus.SENT
        notification.sent_at = utcnow()
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_failed(self, notification_id: int, error_message: str) -> Optional[Notification]:
        notification = self.get_by_id(notification_id)
        if not notification:
            return None
        notification.status = NotificationStatus.FAILED
        notification.failed_at = utcnow()
        notification.error_message = error_message
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        return self.db.query(Notification).filter(Notification.id == notification_id).first()

    # ── List by client (primary) ──────────────────────────────────────────────

    def list_by_client(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Notification]:
        offset = (page - 1) * page_size
        return (
            self.db.query(Notification)
            .filter(Notification.client_id == client_id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def count_by_client(self, client_id: int) -> int:
        return self.db.query(Notification).filter(Notification.client_id == client_id).count()

    # ── List by business (scoped view) ────────────────────────────────────────

    def list_by_business(
        self,
        business_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Notification]:
        offset = (page - 1) * page_size
        return (
            self.db.query(Notification)
            .filter(Notification.business_id == business_id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def count_by_business(self, business_id: int) -> int:
        return self.db.query(Notification).filter(Notification.business_id == business_id).count()

    # ── Paginated list (supports both filters) ────────────────────────────────

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        client_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> tuple[list[Notification], int]:
        """Return paginated notifications and total count.

        client_id filters the primary anchor (all notifications for the legal entity).
        business_id narrows further to a specific business scope.
        """
        q = self.db.query(Notification)
        if client_id is not None:
            q = q.filter(Notification.client_id == client_id)
        if business_id is not None:
            q = q.filter(Notification.business_id == business_id)
        total = q.count()
        items = (
            q.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def list_recent(
        self,
        limit: int = 20,
        client_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> list[Notification]:
        q = self.db.query(Notification)
        if client_id is not None:
            q = q.filter(Notification.client_id == client_id)
        if business_id is not None:
            q = q.filter(Notification.business_id == business_id)
        return q.order_by(Notification.created_at.desc()).limit(limit).all()

    # ── Read state ────────────────────────────────────────────────────────────

    def mark_read(self, notification_ids: list[int]) -> int:
        """Mark specific notifications as read. Returns count updated."""
        now = utcnow()
        count = (
            self.db.query(Notification)
            .filter(Notification.id.in_(notification_ids), Notification.is_read == False)  # noqa: E712
            .update({"is_read": True, "read_at": now}, synchronize_session=False)
        )
        self.db.commit()
        return count

    def mark_all_read(
        self,
        client_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        now = utcnow()
        q = self.db.query(Notification).filter(Notification.is_read == False)  # noqa: E712
        if client_id is not None:
            q = q.filter(Notification.client_id == client_id)
        if business_id is not None:
            q = q.filter(Notification.business_id == business_id)
        count = q.update({"is_read": True, "read_at": now}, synchronize_session=False)
        self.db.commit()
        return count

    def count_unread(
        self,
        client_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> int:
        q = self.db.query(Notification).filter(Notification.is_read == False)  # noqa: E712
        if client_id is not None:
            q = q.filter(Notification.client_id == client_id)
        if business_id is not None:
            q = q.filter(Notification.business_id == business_id)
        return q.count()

    def exists_for_binder_trigger(self, binder_id: int, trigger: NotificationTrigger) -> bool:
        return (
            self.db.query(Notification)
            .filter(Notification.binder_id == binder_id, Notification.trigger == trigger)
            .first()
        ) is not None