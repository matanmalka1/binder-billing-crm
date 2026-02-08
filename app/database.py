from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import config

# Create engine
engine = create_engine(
    config.DATABASE_URL,
    echo=config.APP_ENV == "local",
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schema from ORM models."""
    from app.models import user, client, binder, binder_status_log  # noqa
    Base.metadata.create_all(bind=engine)