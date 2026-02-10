from logging.config import fileConfig
import logging

from sqlalchemy import engine_from_config
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy import pool

from alembic import context

# Import app config and models
from app.config import config as app_config
from app.database import Base
from app.models import (
    User, Client, Binder, BinderStatusLog,
    Charge, Invoice, Notification, PermanentDocument
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic env logger (respects alembic.ini logging config)
logger = logging.getLogger("alembic.env")


def _safe_db_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<invalid DATABASE_URL>"


# Override sqlalchemy.url from app config
config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL)
logger.info(
    "Using APP_ENV=%s DATABASE_URL=%s",
    getattr(app_config, "APP_ENV", "<unknown>"),
    _safe_db_url(app_config.DATABASE_URL),
)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()
    except OperationalError:
        logger.error(
            "Database connection failed for DATABASE_URL=%s",
            _safe_db_url(app_config.DATABASE_URL),
        )
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
