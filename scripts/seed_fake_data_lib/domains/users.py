from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.users.models.user import User, UserRole
from app.users.models.user_audit_log import AuditAction, AuditStatus, UserAuditLog

from ..constants import DEFAULT_PASSWORD_HASH
from ..random_utils import full_name


def create_users(db, rng: Random, cfg) -> list[User]:
    users: list[User] = []
    for i in range(cfg.users):
        role = UserRole.ADVISOR if i % 3 == 0 else UserRole.SECRETARY
        user = User(
            full_name=full_name(rng),
            email=f"user{i + 1}@example.com",
            phone=f"05{rng.randint(10000000, 99999999)}",
            password_hash=DEFAULT_PASSWORD_HASH,
            role=role,
            is_active=rng.random() > 0.1,
            token_version=0,
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(10, 300)),
            last_login_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 30)),
        )
        db.add(user)
        users.append(user)
    db.flush()
    return users


def create_user_audit_logs(db, rng: Random, users: list[User]) -> None:
    for user in users:
        success_log = UserAuditLog(
            action=AuditAction.LOGIN_SUCCESS,
            actor_user_id=user.id,
            target_user_id=user.id,
            email=user.email,
            status=AuditStatus.SUCCESS,
            reason=None,
            metadata_json='{"source":"seed"}',
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 30)),
        )
        db.add(success_log)

        if rng.random() < 0.3:
            fail_log = UserAuditLog(
                action=AuditAction.LOGIN_FAILURE,
                actor_user_id=None,
                target_user_id=user.id,
                email=user.email,
                status=AuditStatus.FAILURE,
                reason="invalid_password",
                metadata_json='{"source":"seed"}',
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 30)),
            )
            db.add(fail_log)
    db.flush()
