from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.businesses.models.business import Business, BusinessStatus
from app.businesses.services.business_lookup import get_business_or_raise


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


def validate_business_for_create(db: Session, business_id: int) -> Business:
    """Fetch business and assert it allows new record creation."""
    business = get_business_or_raise(db, business_id)
    assert_business_allows_create(business)
    return business
