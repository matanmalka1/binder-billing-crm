from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.clients.repositories.client_repository import ClientRepository
from app.clients.models.client import Client, ClientStatus


def get_client_or_raise(db: Session, client_id: int) -> Client:
    """Fetch a client or raise a NotFoundError if missing."""
    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
    return client


def assert_client_allows_create(client: Client) -> None:
    """Raise ForbiddenError if client status blocks new record creation (FROZEN or CLOSED)."""
    if client.status == ClientStatus.CLOSED:
        raise ForbiddenError("לקוח סגור — לא ניתן ליצור עבודה חדשה", "CLIENT.CLOSED")
    if client.status == ClientStatus.FROZEN:
        raise ForbiddenError("לקוח מוקפא — לא ניתן ליצור עבודה חדשה", "CLIENT.FROZEN")


def assert_client_not_closed(client: Client) -> None:
    """Raise ForbiddenError if client is CLOSED (blocks all writes including updates)."""
    if client.status == ClientStatus.CLOSED:
        raise ForbiddenError("לקוח סגור — לא ניתן לבצע פעולות כתיבה", "CLIENT.CLOSED")
