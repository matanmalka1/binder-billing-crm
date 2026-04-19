import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository

_log = logging.getLogger(__name__)

_AUTO_BINDER_STATUS_LOG_OLD_VALUE = "null"
_AUTO_BINDER_STATUS_LOG_NOTES = "קלסר נפתח אוטומטית"


def create_initial_binder(db: Session, client: Client, actor_id: Optional[int]) -> None:
    """
    Open a bare placeholder binder when a new client is created.

    Requires office_client_number to be set on the client.
    If not set, skips creation with a warning — staff must open the first binder
    manually once the office client number is assigned.

    The binder is created with period_start=None (no material received yet).
    """
    if actor_id is None:
        _log.warning("auto-binder skipped for client %s: actor_id is None", client.id)
        return
    if client.office_client_number is None:
        raise ValueError(f"לא ניתן ליצור קלסר: מספר לקוח משרד חסר ללקוח {client.id}")

    binder_repo = BinderRepository(db)
    status_log_repo = BinderStatusLogRepository(db)
    seq = binder_repo.count_all_by_client(client.id) + 1
    binder = binder_repo.create(
        client_id=client.id,
        binder_number=f"{client.office_client_number}/{seq}",
        period_start=None,
        created_by=actor_id,
    )
    status_log_repo.append(
        binder_id=binder.id,
        old_status=_AUTO_BINDER_STATUS_LOG_OLD_VALUE,
        new_status=BinderStatus.IN_OFFICE.value,
        changed_by=actor_id,
        notes=_AUTO_BINDER_STATUS_LOG_NOTES,
    )
