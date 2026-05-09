from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError


class BaseService:
    """
    Thin service base providing session injection and get-or-raise helpers.

    Transaction contract:
    - Read services must NOT call db.commit() or db.rollback().
    - Write services may call db.commit() explicitly only when the existing
      project pattern requires it (e.g., before an external side-effect).
    - Do not rely on get_db() auto-commit as a service-layer contract.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_or_raise(self, repo, entity_id: int, error_code: str):
        """
        Fetch entity via repo.get_by_id(). Raise NotFoundError if None.

        error_code format: "DOMAIN.NOT_FOUND" — e.g. "BINDER.NOT_FOUND"
        """
        entity = repo.get_by_id(entity_id)
        if not entity:
            resource = error_code.split(".")[0].replace("_", " ").title()
            raise NotFoundError(f"{resource} {entity_id} לא נמצא", error_code)
        return entity

    def _get_or_raise_for_update(self, repo, entity_id: int, error_code: str):
        """SELECT … FOR UPDATE variant of _get_or_raise."""
        entity = repo.get_by_id_for_update(entity_id)
        if not entity:
            resource = error_code.split(".")[0].replace("_", " ").title()
            raise NotFoundError(f"{resource} {entity_id} לא נמצא", error_code)
        return entity
