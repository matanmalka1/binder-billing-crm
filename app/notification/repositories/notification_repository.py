from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.notification.models.notification import (
    Notification,
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from app.utils.time_utils import utcnow


class NotificationRepository(BaseRepository[Notification]):
    """Data access layer for Notification entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_record_id: int,
        trigger: NotificationTrigger,
        channel: NotificationChannel,
        recipient: str,
        content_snapshot: str,
        business_id: Optional[int] = None,
        binder_id: Optional[int] = None,
        annual_report_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> Notification:
        notification = Notification(
            client_record_id=client_record_id,
            business_id=business_id,
            binder_id=binder_id,
            annual_report_id=annual_report_id,
            trigger=trigger,
            channel=channel,
            recipient=recipient,
            content_snapshot=content_snapshot,
            status=NotificationStatus.PENDING,
            severity=severity,
            triggered_by=triggered_by,
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def mark_sent(self, notification_id: int) -> Optional[Notification]:
        notification = self.get_by_id(notification_id)
        if not notification:
            return None
        notification.status = NotificationStatus.SENT
        notification.sent_at = utcnow()
        self.db.flush()
        return notification

    def mark_failed(
        self, notification_id: int, error_message: str
    ) -> Optional[Notification]:
        notification = self.get_by_id(notification_id)
        if not notification:
            return None
        notification.status = NotificationStatus.FAILED
        notification.failed_at = utcnow()
        notification.error_message = error_message
        self.db.flush()
        return notification

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        return self.db.scalars(
            select(Notification).where(Notification.id == notification_id)
        ).first()

    def list_by_client_record(
        self,
        client_record_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Notification]:
        offset = (page - 1) * page_size
        return self.db.scalars(
            select(Notification)
            .where(Notification.client_record_id == client_record_id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()

    def count_by_client_record(self, client_record_id: int) -> int:
        return self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.client_record_id == client_record_id
            )
        )

    # ── List by business (scoped view) ────────────────────────────────────────

    def list_by_business(
        self,
        business_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Notification]:
        offset = (page - 1) * page_size
        return self.db.scalars(
            select(Notification)
            .where(Notification.business_id == business_id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()

    def count_by_business(self, business_id: int) -> int:
        return self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.business_id == business_id
            )
        )

    # ── Paginated list (supports both filters) ────────────────────────────────

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> tuple[list[Notification], int]:
        """Return paginated notifications and total count."""
        count_stmt = select(func.count(Notification.id))
        list_stmt = select(Notification)
        if client_record_id is not None:
            count_stmt = count_stmt.where(
                Notification.client_record_id == client_record_id
            )
            list_stmt = list_stmt.where(
                Notification.client_record_id == client_record_id
            )
        if business_id is not None:
            count_stmt = count_stmt.where(Notification.business_id == business_id)
            list_stmt = list_stmt.where(Notification.business_id == business_id)
        total = self.db.scalar(count_stmt)
        items = self.db.scalars(
            list_stmt.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, total

    def list_recent(
        self,
        limit: int = 20,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> list[Notification]:
        stmt = select(Notification)
        if client_record_id is not None:
            stmt = stmt.where(Notification.client_record_id == client_record_id)
        if business_id is not None:
            stmt = stmt.where(Notification.business_id == business_id)
        return self.db.scalars(
            stmt.order_by(Notification.created_at.desc()).limit(limit)
        ).all()

    # ── Read state ────────────────────────────────────────────────────────────

    def mark_read(self, notification_ids: list[int]) -> int:
        """Mark specific notifications as read. Returns count updated."""
        now = utcnow()
        result = self.db.execute(
            update(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=now)
        )
        self.db.flush()
        return result.rowcount

    def mark_all_read(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        now = utcnow()
        stmt = (
            update(Notification)
            .where(Notification.is_read == False)  # noqa: E712
            .values(is_read=True, read_at=now)
        )
        if client_record_id is not None:
            stmt = stmt.where(Notification.client_record_id == client_record_id)
        if business_id is not None:
            stmt = stmt.where(Notification.business_id == business_id)
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount

    def count_unread(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.is_read == False  # noqa: E712
        )
        if client_record_id is not None:
            stmt = stmt.where(Notification.client_record_id == client_record_id)
        if business_id is not None:
            stmt = stmt.where(Notification.business_id == business_id)
        return self.db.scalar(stmt)

    def exists_for_binder_trigger(
        self, binder_id: int, trigger: NotificationTrigger
    ) -> bool:
        return (
            self.db.scalars(
                select(Notification).where(
                    Notification.binder_id == binder_id, Notification.trigger == trigger
                )
            ).first()
            is not None
        )

    def get_last_for_binder_trigger(
        self, binder_id: int, trigger: NotificationTrigger
    ) -> Optional[Notification]:
        return self.db.scalars(
            select(Notification)
            .where(Notification.binder_id == binder_id, Notification.trigger == trigger)
            .order_by(Notification.created_at.desc())
        ).first()

    def get_last_for_annual_report_trigger(
        self, annual_report_id: int, trigger: NotificationTrigger
    ) -> Optional[Notification]:
        return self.db.scalars(
            select(Notification)
            .where(
                Notification.annual_report_id == annual_report_id,
                Notification.trigger == trigger,
            )
            .order_by(Notification.created_at.desc())
        ).first()
