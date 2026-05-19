from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class IdempotencyStatus(str, PyEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), nullable=False)
    route = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_hash = Column(String(64), nullable=False)
    status = Column(pg_enum(IdempotencyStatus), nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("key", "route", "user_id", name="pk_idempotency_keys"),
    )
