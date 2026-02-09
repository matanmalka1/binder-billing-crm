from sqlalchemy.orm import Session


class HealthRepository:
    """Repository for readiness DB connectivity checks."""

    def __init__(self, db: Session):
        self.db = db

    def can_connect(self) -> bool:
        """
        Return True if a simple ORM query succeeds, else False.

        Must not use raw SQL.
        """
        try:
            self.db.query(1).first()
            return True
        except Exception:
            return False
