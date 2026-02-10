import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    binders,
    binders_history,
    binders_operations,
    charge,
    clients,
    clients_binders,
    dashboard,
    dashboard_overview,
    health,
    permanent_documents,
    dashboard_extended,
    timeline,
    search,
)
from app.config import config
from app.core import EnvValidator, get_logger, setup_exception_handlers, setup_logging
from app.middleware.request_id import RequestIDMiddleware

# Validate environment before starting
EnvValidator.validate()

# Setup structured logging
setup_logging(level=config.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with graceful startup and shutdown."""
    logger.info("Application starting")
    if config.APP_ENV == "development":
        from app.database import Base, engine
        import app.models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        logger.info("Development schema ensured (ORM create_all)")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="Binder & Billing CRM",
    version="1.0.0",
    lifespan=lifespan,
)

# Root endpoint (simple service presence check)
@app.get("/")
def root():
    return {
        "service": "binder-billing-crm",
        "status": "running",
    }

# Setup exception handlers
setup_exception_handlers(app)

# Request ID middleware (before CORS)
app.add_middleware(RequestIDMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/info")
def info():
    return {
        "app": "Binder Billing CRM",
        "env": config.APP_ENV,
    }


# API routes
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
# NOTE: include operational binder routes before `/binders/{binder_id}` to avoid path conflicts.
app.include_router(binders_operations.router, prefix="/api/v1")
app.include_router(binders.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(clients_binders.router, prefix="/api/v1")
app.include_router(dashboard_overview.router, prefix="/api/v1")
app.include_router(binders_history.router, prefix="/api/v1")
app.include_router(charge.router, prefix="/api/v1")
app.include_router(permanent_documents.router, prefix="/api/v1")
app.include_router(dashboard_extended.router, prefix="/api/v1")
app.include_router(timeline.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")



def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    sys.exit(0)


# Register shutdown handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)
