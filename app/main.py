from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    binders,
    binders_history,
    binders_operations,
    clients,
    clients_binders,
    dashboard,
    dashboard_overview,
)
from app.config import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: no DB auto-creation."""
    yield


app = FastAPI(
    title="Binder & Billing CRM",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/info")
def info():
    return {
        "app": "Binder Billing CRM",
        "env": config.APP_ENV,
    }

# API routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(binders.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(binders_operations.router, prefix="/api/v1")
app.include_router(clients_binders.router, prefix="/api/v1")
app.include_router(dashboard_overview.router, prefix="/api/v1")
app.include_router(binders_history.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)
