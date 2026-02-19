import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.advance_payments.api import advance_payments
from app.annual_reports.api import (
    annual_report_client,
    annual_report_create_read,
    annual_report_detail,
    annual_report_schedule,
    annual_report_season,
    annual_report_status,
)
from app.binders.api import binders, binders_history, binders_operations
from app.clients.api import client_tax_profile, clients, clients_binders, clients_excel
from app.dashboard.api import dashboard, dashboard_extended, dashboard_overview, dashboard_tax
from app.users.api import users, users_audit
from app.signature_requests.api import routers as signature_requests_routers
from app.authority_contact.api import authority_contact
from app.charge.api import charge
from app.config import config
from app.core import EnvValidator, get_logger, setup_exception_handlers, setup_logging
from app.correspondence.api import correspondence
from app.health.api import health
from app.middleware.request_id import RequestIDMiddleware
from app.permanent_documents.api import permanent_documents
from app.reminders.api import routers as reminders
from app.reports.api import reports
from app.search.api import search
from app.tax_deadline.api import tax_deadline
from app.timeline.api import timeline
from app.users.api import auth

EnvValidator.validate()

setup_logging(level=config.LOG_LEVEL)
logger = get_logger(__name__)
if config.APP_ENV == "development":
    logger.info("CORS allowed origins: %s", config.CORS_ALLOWED_ORIGINS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with graceful startup and shutdown."""
    logger.info("Application starting")
    if config.APP_ENV == "development":
        from app.database import Base, engine

        Base.metadata.create_all(bind=engine)
        logger.info("Development schema ensured (ORM create_all)")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="Binder & Billing CRM",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/")
def root():
    return {
        "service": "binder-billing-crm",
        "status": "running",
    }

setup_exception_handlers(app)

app.add_middleware(RequestIDMiddleware)

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


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(annual_report_detail.router, prefix="/api/v1")
app.include_router(annual_report_create_read.router, prefix="/api/v1")
app.include_router(annual_report_schedule.router, prefix="/api/v1")
app.include_router(annual_report_status.router, prefix="/api/v1")
app.include_router(annual_report_client.clients_router, prefix="/api/v1")
app.include_router(annual_report_season.season_router, prefix="/api/v1")
app.include_router(tax_deadline.router, prefix="/api/v1")
app.include_router(authority_contact.router, prefix="/api/v1")
app.include_router(dashboard_tax.router, prefix="/api/v1")
# Place Excel routes before parameterized /clients/{id} to avoid path conflicts
app.include_router(clients_excel.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(binders_operations.router, prefix="/api/v1")
app.include_router(binders.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(clients_binders.router, prefix="/api/v1")
app.include_router(dashboard_overview.router, prefix="/api/v1")
app.include_router(binders_history.router, prefix="/api/v1")
app.include_router(charge.router, prefix="/api/v1")
app.include_router(permanent_documents.router, prefix="/api/v1")
app.include_router(dashboard_extended.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(timeline.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(users_audit.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(client_tax_profile.router, prefix="/api/v1")
app.include_router(correspondence.router, prefix="/api/v1")
app.include_router(advance_payments.router, prefix="/api/v1")
app.include_router(signature_requests_routers.router, prefix="/api/v1")
app.include_router(signature_requests_routers.signer_router)

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)
