"""align annual report domain with main-return model

Revision ID: 0003_align_annual_report_domain_with_main_return_model
Revises: 0002_fix_tax_deadline_advance_payment_check_constraint
Create Date: 2026-04-14

Changes:
- Add annual report form `1214`
- Remap corporation annual reports from `6111` to `1214`
- Enforce one main annual report per `(client_id, tax_year)`
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.utils.enum_utils


revision: str = "0003_align_annual_report_domain_with_main_return_model"
down_revision: Union[str, Sequence[str], None] = "0002_fix_tax_deadline_advance_payment_check_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD_FORM_ENUM = app.utils.enum_utils._NormalizedEnum(
    "1301",
    "1215",
    "6111",
    name="annualreportform",
)

_NEW_FORM_ENUM = app.utils.enum_utils._NormalizedEnum(
    "0135",
    "1301",
    "1214",
    "1215",
    "6111",
    name="annualreportform",
)

_OLD_CLIENT_TYPE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "individual",
    "self_employed",
    "corporation",
    "partnership",
    name="clienttypeforreport",
)

_NEW_CLIENT_TYPE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "individual",
    "self_employed",
    "corporation",
    "public_institution",
    "partnership",
    "control_holder",
    "exempt_dealer",
    name="clienttypeforreport",
)

_OLD_REPORT_TYPE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "individual",
    "self_employed",
    "company",
    name="annualreporttype",
)

_NEW_REPORT_TYPE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "individual",
    "self_employed",
    "company",
    "public_institution",
    "exempt_dealer",
    name="annualreporttype",
)

_OLD_SCHEDULE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "schedule_b",
    "schedule_bet",
    "schedule_gimmel",
    "schedule_dalet",
    "schedule_heh",
    "schedule_a",
    "schedule_vav",
    "annex_15",
    "annex_867",
    name="annualreportschedule",
)

_NEW_SCHEDULE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "schedule_b",
    "schedule_bet",
    "schedule_gimmel",
    "schedule_dalet",
    "schedule_heh",
    "schedule_a",
    "schedule_vav",
    "annex_15",
    "annex_867",
    "form_1399",
    "form_150",
    "form_1504",
    "form_6111",
    "form_1344",
    "form_1350",
    "form_1327",
    "form_1342",
    "form_1343",
    "form_1348",
    "form_858",
    name="annualreportschedule",
)


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE annualreportform ADD VALUE IF NOT EXISTS '1214'")
        op.execute("ALTER TYPE annualreportform ADD VALUE IF NOT EXISTS '0135'")
        op.execute("ALTER TYPE clienttypeforreport ADD VALUE IF NOT EXISTS 'public_institution'")
        op.execute("ALTER TYPE clienttypeforreport ADD VALUE IF NOT EXISTS 'control_holder'")
        op.execute("ALTER TYPE clienttypeforreport ADD VALUE IF NOT EXISTS 'exempt_dealer'")
        op.execute("ALTER TYPE annualreporttype ADD VALUE IF NOT EXISTS 'public_institution'")
        op.execute("ALTER TYPE annualreporttype ADD VALUE IF NOT EXISTS 'exempt_dealer'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1399'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_150'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1504'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_6111'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1344'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1350'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1327'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1342'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1343'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_1348'")
        op.execute("ALTER TYPE annualreportschedule ADD VALUE IF NOT EXISTS 'form_858'")
    else:
        with op.batch_alter_table("annual_reports", schema=None) as batch_op:
            batch_op.alter_column(
                "form_type",
                existing_type=_OLD_FORM_ENUM,
                type_=_NEW_FORM_ENUM,
                existing_nullable=False,
            )
            batch_op.alter_column(
                "client_type",
                existing_type=_OLD_CLIENT_TYPE_ENUM,
                type_=_NEW_CLIENT_TYPE_ENUM,
                existing_nullable=False,
            )
            batch_op.alter_column(
                "report_type",
                existing_type=_OLD_REPORT_TYPE_ENUM,
                type_=_NEW_REPORT_TYPE_ENUM,
                existing_nullable=False,
            )
        with op.batch_alter_table("annual_report_schedules", schema=None) as batch_op:
            batch_op.alter_column(
                "schedule",
                existing_type=_OLD_SCHEDULE_ENUM,
                type_=_NEW_SCHEDULE_ENUM,
                existing_nullable=False,
            )
        with op.batch_alter_table("annual_report_annex_data", schema=None) as batch_op:
            batch_op.alter_column(
                "schedule",
                existing_type=_OLD_SCHEDULE_ENUM,
                type_=_NEW_SCHEDULE_ENUM,
                existing_nullable=False,
            )

    op.execute(
        sa.text(
            "UPDATE annual_reports "
            "SET form_type = '1214' "
            "WHERE client_type = 'corporation' AND form_type = '6111'"
        )
    )

    op.drop_index("idx_annual_report_client_year_type", table_name="annual_reports")
    op.create_index(
        "idx_annual_report_client_year_type",
        "annual_reports",
        ["client_id", "tax_year"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("idx_annual_report_client_year_type", table_name="annual_reports")
    op.create_index(
        "idx_annual_report_client_year_type",
        "annual_reports",
        ["client_id", "tax_year", "report_type"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        sa.text(
            "UPDATE annual_reports "
            "SET form_type = '6111' "
            "WHERE client_type = 'corporation' AND form_type = '1214'"
        )
    )

    if bind.dialect.name != "postgresql":
        with op.batch_alter_table("annual_report_annex_data", schema=None) as batch_op:
            batch_op.alter_column(
                "schedule",
                existing_type=_NEW_SCHEDULE_ENUM,
                type_=_OLD_SCHEDULE_ENUM,
                existing_nullable=False,
            )
        with op.batch_alter_table("annual_report_schedules", schema=None) as batch_op:
            batch_op.alter_column(
                "schedule",
                existing_type=_NEW_SCHEDULE_ENUM,
                type_=_OLD_SCHEDULE_ENUM,
                existing_nullable=False,
            )
        with op.batch_alter_table("annual_reports", schema=None) as batch_op:
            batch_op.alter_column(
                "form_type",
                existing_type=_NEW_FORM_ENUM,
                type_=_OLD_FORM_ENUM,
                existing_nullable=False,
            )
            batch_op.alter_column(
                "client_type",
                existing_type=_NEW_CLIENT_TYPE_ENUM,
                type_=_OLD_CLIENT_TYPE_ENUM,
                existing_nullable=False,
            )
            batch_op.alter_column(
                "report_type",
                existing_type=_NEW_REPORT_TYPE_ENUM,
                type_=_OLD_REPORT_TYPE_ENUM,
                existing_nullable=False,
            )
