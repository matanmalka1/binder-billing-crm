"""add_domain_identity_unique_constraints

Revision ID: 0020_add_domain_identity_unique_constraints
Revises: 0019_drop_client_id_from_workflow_tables
Create Date: 2026-04-20

Adds three partial unique indexes enforcing domain identity constraints:

1. annual_reports: UNIQUE (client_record_id, tax_year) WHERE deleted_at IS NULL
2. tax_deadlines:  UNIQUE (client_record_id, deadline_type, period) WHERE deleted_at IS NULL AND period IS NOT NULL
                   UNIQUE (client_record_id, deadline_type)          WHERE deleted_at IS NULL AND period IS NULL
3. vat_work_items: UNIQUE (client_record_id, period)                 WHERE deleted_at IS NULL

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0020_add_domain_identity_unique_constraints
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0019_drop_client_id_from_workflow_tables
"""

from alembic import op
import sqlalchemy as sa

revision = "0020_add_domain_identity_unique_constraints"
down_revision = "0019_drop_client_id_from_workflow_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. AnnualReport: UNIQUE (client_record_id, tax_year) WHERE deleted_at IS NULL ──
    op.create_index(
        "uq_annual_reports_client_record_tax_year",
        "annual_reports",
        ["client_record_id", "tax_year"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND client_record_id IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND client_record_id IS NOT NULL"),
    )

    # ── 2a. TaxDeadline: UNIQUE (client_record_id, deadline_type, period) WHERE period IS NOT NULL ──
    op.create_index(
        "uq_tax_deadlines_client_record_type_period",
        "tax_deadlines",
        ["client_record_id", "deadline_type", "period"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND period IS NOT NULL AND client_record_id IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND period IS NOT NULL AND client_record_id IS NOT NULL"),
    )

    # ── 2b. TaxDeadline: UNIQUE (client_record_id, deadline_type) WHERE period IS NULL (annual_report) ──
    op.create_index(
        "uq_tax_deadlines_client_record_type_no_period",
        "tax_deadlines",
        ["client_record_id", "deadline_type"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND period IS NULL AND client_record_id IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND period IS NULL AND client_record_id IS NOT NULL"),
    )

    # ── 3. VatWorkItem: UNIQUE (client_record_id, period) WHERE deleted_at IS NULL ──
    op.create_index(
        "uq_vat_work_items_client_record_period",
        "vat_work_items",
        ["client_record_id", "period"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND client_record_id IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND client_record_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_vat_work_items_client_record_period", table_name="vat_work_items")
    op.drop_index("uq_tax_deadlines_client_record_type_no_period", table_name="tax_deadlines")
    op.drop_index("uq_tax_deadlines_client_record_type_period", table_name="tax_deadlines")
    op.drop_index("uq_annual_reports_client_record_tax_year", table_name="annual_reports")
