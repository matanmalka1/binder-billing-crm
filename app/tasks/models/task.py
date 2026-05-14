from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from app.database import Base
from app.users.models.user import UserRole
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class TaskStatus(str, PyEnum):
    OPEN = "open"
    DONE = "done"
    CANCELED = "canceled"


class TaskPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    # pg_enum uses values_callable so DB stores lowercase values ("open", "done", ...)
    # matching the taskstatus / taskpriority PostgreSQL enum types created in migration 0004_tasks.
    status = Column(
        pg_enum(TaskStatus, name="taskstatus"), nullable=False, default=TaskStatus.OPEN
    )
    priority = Column(
        pg_enum(TaskPriority, name="taskpriority"),
        nullable=False,
        default=TaskPriority.NORMAL,
    )
    due_date = Column(Date, nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_role = Column(
        pg_enum(UserRole, name="userrole", create_type=False), nullable=True
    )
    source_domain = Column(String(100), nullable=True)
    source_id = Column(Integer, nullable=True)
    action_key = Column(String(100), nullable=True)
    action_payload = Column(JSON, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    canceled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_due_date", "due_date"),
        Index("idx_tasks_assigned_to_user_id", "assigned_to_user_id"),
        Index("idx_tasks_source", "source_domain", "source_id"),
    )
