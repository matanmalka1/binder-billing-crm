"""
Health check endpoint for production readiness.

Provides:
- Unauthenticated health status
- Database connectivity verification
- Read-only operation
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.health.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Health check endpoint.
    
    Verifies:
    - Application is running
    - Database connection is available
    
    Returns 200 if healthy, 503 if unhealthy.
    """
    result = HealthService(db).check()
    if result["status"] != "healthy":
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=result)
    return result
