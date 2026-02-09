from sqlalchemy.orm import Session

from app.repositories.health_repository import HealthRepository


class HealthService:
    """Service for health/readiness checks."""

    def __init__(self, db: Session):
        self.health_repo = HealthRepository(db)

    def check(self) -> dict[str, str]:
        db_ok = self.health_repo.can_connect()
        return {
            "status": "healthy" if db_ok else "unhealthy",
            "database": "connected" if db_ok else "disconnected",
        }
