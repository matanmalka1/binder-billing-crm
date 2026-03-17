from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# Load app config for DATABASE_URL
from app.config import config as app_config

# Import all models so Alembic can detect them for autogenerate
import app.advance_payments.models.advance_payment  # noqa: F401
import app.annual_reports.models.annual_report_detail  # noqa: F401
import app.annual_reports.models.annual_report_model  # noqa: F401
import app.annual_reports.models.annual_report_schedule_entry  # noqa: F401
import app.annual_reports.models.annual_report_status_history  # noqa: F401
import app.authority_contact.models.authority_contact  # noqa: F401
import app.binders.models.binder  # noqa: F401
import app.binders.models.binder_status_log  # noqa: F401
import app.charge.models.charge  # noqa: F401
import app.clients.models.client  # noqa: F401
import app.clients.models.client_tax_profile  # noqa: F401
import app.correspondence.models.correspondence  # noqa: F401
import app.invoice.models.invoice  # noqa: F401
import app.notification.models.notification  # noqa: F401
import app.permanent_documents.models.permanent_document  # noqa: F401
import app.reminders.models.reminder  # noqa: F401
import app.signature_requests.models.signature_request  # noqa: F401
import app.tax_deadline.models.tax_deadline  # noqa: F401
import app.users.models.user  # noqa: F401
import app.users.models.user_audit_log  # noqa: F401
import app.users.models.user_management  # noqa: F401
import app.vat_reports.models.vat_audit_log  # noqa: F401
import app.vat_reports.models.vat_invoice  # noqa: F401
import app.vat_reports.models.vat_work_item  # noqa: F401

from app.database import Base

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

alembic_config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = alembic_config.get_main_option("sqlalchemy.url")
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
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Widen alembic_version.version_num if needed (default VARCHAR(32) is too short
        # for descriptive revision IDs like "0006_annual_report_income_expense_and_fks")
        dialect = connectable.dialect.name
        if dialect == "postgresql":
            exists = connection.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'alembic_version')"
            )).scalar()
            if exists:
                connection.execute(text(
                    "ALTER TABLE alembic_version "
                    "ALTER COLUMN version_num TYPE VARCHAR(255)"
                ))
                connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
