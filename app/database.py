from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import config


if config.APP_ENV == "production" and config.DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("SQLite אינו מותר בסביבת ייצור")

# Create engine
engine = create_engine(
    config.DATABASE_URL,
    echo=config.APP_ENV == "development",
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes to get DB session.

    Commits on clean exit; rolls back on any exception.
    Services that coordinate external I/O (e.g. storage uploads) may call
    db.commit() / db.rollback() themselves — the safety net here is a no-op
    on top of an already-committed session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
