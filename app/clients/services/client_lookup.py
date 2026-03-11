from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.clients.repositories.client_repository import ClientRepository
from app.clients.models.client import Client


def get_client_or_raise(db: Session, client_id: int) -> Client:
    """Fetch a client or raise a NotFoundError if missing."""
    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
    return client
