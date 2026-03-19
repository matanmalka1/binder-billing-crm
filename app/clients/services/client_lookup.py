from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.clients.repositories.client_repository import ClientRepository
from app.clients.models.client import Client
from app.business.models.business import Business, BusinessStatus


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