from app.core.exceptions import NotFoundError
from app.users.repositories.user_repository import UserRepository


def get_user_or_raise(repo: UserRepository, user_id: int):
    """Fetch a user or raise NotFoundError if missing."""
    user = repo.get_by_id(user_id)
    if not user:
        raise NotFoundError(f"משתמש {user_id} לא נמצא", "USER.NOT_FOUND")
    return user
