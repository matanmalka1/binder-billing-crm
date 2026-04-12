from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# Load app config for DATABASE_URL
from app.config import config as app_config

# Import all models so Alembic can detect them for autogenerate
import app.businesses.models.business          # noqa
import app.clients.models.client               # noqa
import app.users.models.user                   # noqa
import app.users.models.user_audit_log         # noqa
import app.binders.models.binder               # noqa
import app.binders.models.binder_intake        # noqa
import app.binders.models.binder_intake_material  # noqa
import app.binders.models.binder_status_log    # noqa
import app.annual_reports.models.annual_report_model   # noqa
import app.annual_reports.models.annual_report_detail  # noqa
import app.annual_reports.models.annual_report_status_history  # noqa
import app.annual_reports.models.annual_report_schedule_entry  # noqa
import app.annual_reports.models.annual_report_annex_data      # noqa
import app.annual_reports.models.annual_report_income_line     # noqa
import app.annual_reports.models.annual_report_expense_line    # noqa
import app.annual_reports.models.annual_report_credit_point_reason    # noqa
import app.vat_reports.models.vat_work_item    # noqa
import app.vat_reports.models.vat_invoice      # noqa
import app.vat_reports.models.vat_audit_log    # noqa
import app.charge.models.charge                # noqa
import app.invoice.models.invoice              # noqa
import app.advance_payments.models.advance_payment  # noqa
import app.tax_deadline.models.tax_deadline    # noqa
import app.reminders.models.reminder           # noqa
import app.notification.models.notification    # noqa
import app.permanent_documents.models.permanent_document  # noqa
import app.signature_requests.models.signature_request    # noqa
import app.correspondence.models.correspondence  # noqa
import app.audit.models.entity_audit_log  # noqa
import app.authority_contact.models.authority_contact  # noqa
import app.notes.models.entity_note  # noqa
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


def _widen_alembic_version_if_needed(connectable) -> None:
    """Widen version_num on existing alembic_version table (PostgreSQL only).

    Uses a separate connection so the commit does not interfere with
    Alembic's own migration transaction.
    """
    with connectable.connect() as conn:
        exists = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'alembic_version')"
        )).scalar()
        if exists:
            conn.execute(text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(255)"
            ))
            conn.commit()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    if connectable.dialect.name == "postgresql":
        _widen_alembic_version_if_needed(connectable)

    with connectable.connect() as connection:
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
