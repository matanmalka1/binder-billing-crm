from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text

from app.database import Base
from app.utils.time import utcnow


class AuditAction(str, PyEnum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    PASSWORD_RESET = "password_reset"


class AuditStatus(str, PyEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class UserAuditLog(Base):
    __tablename__ = "user_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    status = Column(Enum(AuditStatus), nullable=False, index=True)
    reason = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)

