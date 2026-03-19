from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.businesses.models.business import Business
from app.businesses.repositories.business_repository import BusinessRepository


def get_business_or_raise(db: Session, business_id: int) -> Business:
    """Fetch a business or raise NotFoundError."""
    business = BusinessRepository(db).get_by_id(business_id)
    if not business:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
    return business
