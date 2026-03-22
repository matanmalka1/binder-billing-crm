from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.core import EnvValidator, get_logger, setup_exception_handlers, setup_logging
from app.middleware.request_id import RequestIDMiddleware
from app.lifespan import lifespan
from app.router_registry import register_routers

EnvValidator.validate()

setup_logging(level=config.LOG_LEVEL)
logger = get_logger(__name__)
if config.APP_ENV == "development":
    logger.info("CORS allowed origins: %s", config.CORS_ALLOWED_ORIGINS)

app = FastAPI(
    title="Binder & Billing CRM",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {"service": "binder-billing-crm", "status": "running"}


@app.get("/info")
def info():
    return {"app": "Binder Billing CRM", "env": config.APP_ENV}


# All handlers (including AppError and ValueError) are registered inside
# setup_exception_handlers — no need to add them separately here.
setup_exception_handlers(app)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routers(app)

if config.APP_ENV in ("development", "test"):
    from fastapi.staticfiles import StaticFiles
    import os
    os.makedirs("./storage", exist_ok=True)
    app.mount("/local-storage", StaticFiles(directory="./storage"), name="local-storage")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)