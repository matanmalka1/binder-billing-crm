from fastapi import Depends
from sqlalchemy.orm import Session

from app.users.api.deps import get_db, require_role
from app.users.models.user import User, UserRole


def advisor_or_secretary(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY)),
):
    return db, user
