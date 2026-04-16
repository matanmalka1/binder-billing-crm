import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.clients.constants import (
    AUTO_BINDER_INITIAL_STATUS,
    AUTO_BINDER_SEQUENCE,
    AUTO_BINDER_STATUS_LOG_NOTES,
    AUTO_BINDER_STATUS_LOG_OLD_VALUE,
)

_log = logging.getLogger(__name__)


def create_initial_binder(db: Session, client: Client, actor_id: Optional[int]) -> None:
    """Auto-open a bare binder (no intake) when a new client is created."""
    if actor_id is None:
        _log.warning("auto-binder skipped for client %s: actor_id is None", client.id)
        return
    binder_repo = BinderRepository(db)
    status_log_repo = BinderStatusLogRepository(db)
    binder = binder_repo.create(
        client_id=client.id,
        binder_number=f"{client.id}/{AUTO_BINDER_SEQUENCE}",
        period_start=date.today(),
        created_by=actor_id,
    )
    status_log_repo.append(
        binder_id=binder.id,
        old_status=AUTO_BINDER_STATUS_LOG_OLD_VALUE,
        new_status=AUTO_BINDER_INITIAL_STATUS,
        changed_by=actor_id,
        notes=AUTO_BINDER_STATUS_LOG_NOTES,
    )
