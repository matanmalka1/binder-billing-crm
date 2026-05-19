from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.idempotency.model import IdempotencyKey, IdempotencyStatus
from app.utils.time_utils import utcnow


class IdempotencyKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str, route: str, user_id: int) -> IdempotencyKey | None:
        return self.db.scalars(
            select(IdempotencyKey).where(
                IdempotencyKey.key == key,
                IdempotencyKey.route == route,
                IdempotencyKey.user_id == user_id,
            )
        ).first()

    def reserve(
        self,
        *,
        key: str,
        route: str,
        user_id: int,
        request_hash: str,
    ) -> IdempotencyKey:
        """Insert IN_PROGRESS row. Caller must handle IntegrityError on conflict."""
        row = IdempotencyKey(
            key=key,
            route=route,
            user_id=user_id,
            request_hash=request_hash,
            status=IdempotencyStatus.IN_PROGRESS,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def complete(
        self,
        row: IdempotencyKey,
        *,
        response_status: int,
        response_body: Any,
    ) -> None:
        row.status = IdempotencyStatus.COMPLETED
        row.response_status = response_status
        row.response_body = response_body
        row.completed_at = utcnow()
        self.db.flush()

    def release(self, row: IdempotencyKey) -> None:
        """Delete a stale IN_PROGRESS row so the caller can retry."""
        self.db.delete(row)
        self.db.flush()
