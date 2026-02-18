from fastapi import Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole


def advisor_or_secretary(
    db: DBSession = Depends(), user: CurrentUser = Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))
):
    return db, user
