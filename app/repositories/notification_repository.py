from typing import Optional

from sqlalchemy.orm import Session

from app.models import Notification, NotificationChannel, NotificationStatus, NotificationTrigger
from app.utils.time import utcnow


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
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_sent(self, notification_id: int) -> Optional[Notification]:
        """Mark notification as successfully sent."""
        notification = self.get_by_id(notification_id)
        if not notification:
            return None

        notification.status = NotificationStatus.SENT
        notification.sent_at = utcnow()
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_failed(self, notification_id: int, error_message: str) -> Optional[Notification]:
        """Mark notification as failed with error message."""
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
        """Retrieve notification by ID."""
        return self.db.query(Notification).filter(Notification.id == notification_id).first()

    def exists_for_binder_trigger(self, binder_id: int, trigger: NotificationTrigger) -> bool:
        """Check if a notification already exists for a binder and trigger."""
        existing = (
            self.db.query(Notification.id)
            .filter(
                Notification.binder_id == binder_id,
                Notification.trigger == trigger,
            )
            .first()
        )
        return existing is not None

    def list_by_client(self, client_id: int, page: int = 1, page_size: int = 20) -> list[Notification]:
        """List notifications for a client with pagination."""
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
        """Count notifications for a client."""
        return self.db.query(Notification).filter(Notification.client_id == client_id).count()
