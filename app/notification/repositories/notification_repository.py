from typing import Optional

from sqlalchemy.orm import Session

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
        client_id: int,
        trigger: NotificationTrigger,
        channel: NotificationChannel,
        recipient: str,
        content_snapshot: str,
        binder_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> Notification:
        """Create new notification record."""
        notification = Notification(
            client_id=client_id,
            binder_id=binder_id,
            trigger=trigger,
            channel=channel,
            recipient=recipient,
            content_snapshot=content_snapshot,
            status=NotificationStatus.PENDING,
            severity=severity,
        )
        if triggered_by is not None:
            notification.triggered_by = triggered_by
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

    def list_by_client(self, client_id: int, page: int = 1, page_size: int = 20) -> list[Notification]:
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

    def mark_all_read(self, client_id: Optional[int] = None) -> int:
        """Mark all unread notifications (optionally scoped to client). Returns count updated."""
        now = utcnow()
        q = self.db.query(Notification).filter(Notification.is_read == False)  # noqa: E712
        if client_id is not None:
            q = q.filter(Notification.client_id == client_id)
        count = q.update({"is_read": True, "read_at": now}, synchronize_session=False)
        self.db.commit()
        return count

    def count_unread(self, client_id: Optional[int] = None) -> int:
        """Count unread notifications (optionally scoped to client)."""
        q = self.db.query(Notification).filter(Notification.is_read == False)  # noqa: E712
        if client_id is not None:
            q = q.filter(Notification.client_id == client_id)
        return q.count()

    def list_recent(self, limit: int = 20, client_id: Optional[int] = None) -> list[Notification]:
        """Return recent notifications ordered by created_at desc."""
        q = self.db.query(Notification)
        if client_id is not None:
            q = q.filter(Notification.client_id == client_id)
        return q.order_by(Notification.created_at.desc()).limit(limit).all()
