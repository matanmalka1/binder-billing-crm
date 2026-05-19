import logging
from time import perf_counter

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import config
from app.core.logging_config import (
    clear_request_id,
    clear_request_log_stats,
    get_logger,
    get_request_log_stats,
    log_request_summary,
    record_sql_query,
)

logger = get_logger(__name__)

if config.APP_ENV == "production" and config.DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("SQLite אינו מותר בסביבת ייצור")

# Create engine
engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


@event.listens_for(engine, "before_cursor_execute")
def _record_query_start(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _record_query_end(conn, cursor, statement, parameters, context, executemany):
    start_time = getattr(context, "_query_start_time", None)
    if start_time is None:
        return

    record_sql_query(statement, (perf_counter() - start_time) * 1000)

logging.getLogger("sqlalchemy.engine").setLevel(
    logging.INFO if config.APP_ENV == "development" else logging.WARNING
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
        if get_request_log_stats() is not None:
            log_request_summary(logger)
            clear_request_log_stats()
            clear_request_id()
