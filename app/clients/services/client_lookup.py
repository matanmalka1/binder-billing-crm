from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.clients.repositories.client_repository import ClientRepository
from app.clients.models.client import Client, ClientStatus
from app.businesses.models.business import Business, BusinessStatus


def get_client_or_raise(db: Session, client_id: int) -> Client:
    """Fetch a client or raise NotFoundError."""
    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
    return client


def assert_business_allows_create(business: Business) -> None:
    """Raise ForbiddenError if business status blocks new record creation."""
    if business.status == BusinessStatus.CLOSED:
        raise ForbiddenError(
            "עסק סגור — לא ניתן ליצור עבודה חדשה",
            "BUSINESS.CLOSED",
        )
    if business.status == BusinessStatus.FROZEN:
        raise ForbiddenError(
            "עסק מוקפא — לא ניתן ליצור עבודה חדשה",
            "BUSINESS.FROZEN",
        )


def assert_business_not_closed(business: Business) -> None:
    """Raise ForbiddenError if business is CLOSED."""
    if business.status == BusinessStatus.CLOSED:
        raise ForbiddenError(
            "עסק סגור — לא ניתן לבצע פעולות כתיבה",
            "BUSINESS.CLOSED",
        )


def assert_client_allows_create(client: Client) -> None:
    """
    Backward-compatible wrapper for legacy tests/modules.
    New code should call assert_business_allows_create.
    """
    if client.status == ClientStatus.CLOSED:
        raise ForbiddenError(
            "לקוח סגור — לא ניתן ליצור עבודה חדשה",
            "CLIENT.CLOSED",
        )
    if client.status == ClientStatus.FROZEN:
        raise ForbiddenError(
            "לקוח מוקפא — לא ניתן ליצור עבודה חדשה",
            "CLIENT.FROZEN",
        )


def assert_client_not_closed(client: Client) -> None:
    """
    Backward-compatible wrapper for legacy tests/modules.
    New code should call assert_business_not_closed.
    """
    if client.status == ClientStatus.CLOSED:
        raise ForbiddenError(
            "לקוח סגור — לא ניתן לבצע פעולות כתיבה",
            "CLIENT.CLOSED",
        )
