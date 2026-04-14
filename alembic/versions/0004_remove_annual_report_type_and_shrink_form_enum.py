"""remove annual report type and shrink form enum

Revision ID: 0004_remove_annual_report_type_and_shrink_form_enum
Revises: 0003_align_annual_report_domain_with_main_return_model
Create Date: 2026-04-14

Changes:
- Drop duplicated annual_reports.report_type
- Restrict annual report main forms to 1301/1214/1215
- Remap legacy form_type values 0135/6111 into valid main forms
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.utils.enum_utils


revision: str = "0004_remove_annual_report_type_and_shrink_form_enum"
down_revision: Union[str, Sequence[str], None] = "0003_align_annual_report_domain_with_main_return_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD_FORM_ENUM = app.utils.enum_utils._NormalizedEnum(
    "0135",
    "1301",
    "1214",
    "1215",
    "6111",
    name="annualreportform",
)

_NEW_FORM_ENUM = app.utils.enum_utils._NormalizedEnum(
    "1301",
    "1214",
    "1215",
    name="annualreportform",
)

_REPORT_TYPE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "individual",
    "self_employed",
    "company",
    "public_institution",
    "exempt_dealer",
    name="annualreporttype",
)


_UPGRADE_FORM_REMAP_SQL = sa.text(
    """
    UPDATE annual_reports
    SET form_type = CASE
        WHEN form_type = '0135' THEN '1301'
        WHEN form_type = '6111' THEN CASE
            WHEN client_type = 'corporation' THEN '1214'
            WHEN client_type = 'public_institution' THEN '1215'
            ELSE '1301'
        END
        ELSE form_type
    END
    """
)

_DOWNGRADE_REPORT_TYPE_SQL = sa.text(
    """
    UPDATE annual_reports
    SET report_type = CASE
        WHEN client_type = 'self_employed' THEN 'self_employed'
        WHEN client_type = 'partnership' THEN 'self_employed'
        WHEN client_type = 'corporation' THEN 'company'
        WHEN client_type = 'public_institution' THEN 'public_institution'
        WHEN client_type = 'exempt_dealer' THEN 'exempt_dealer'
        ELSE 'individual'
    END
    """
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(_UPGRADE_FORM_REMAP_SQL)

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE annualreportform RENAME TO annualreportform_old")
        op.execute("CREATE TYPE annualreportform AS ENUM ('1301', '1214', '1215')")
        op.execute(
            """
            ALTER TABLE annual_reports
            ALTER COLUMN form_type TYPE annualreportform
            USING form_type::text::annualreportform
            """
        )
        with op.batch_alter_table("annual_reports", schema=None) as batch_op:
            batch_op.drop_column("report_type")
        op.execute("DROP TYPE annualreportform_old")
        op.execute("DROP TYPE IF EXISTS annualreporttype")
    else:
        with op.batch_alter_table("annual_reports", schema=None) as batch_op:
            batch_op.alter_column(
                "form_type",
                existing_type=_OLD_FORM_ENUM,
                type_=_NEW_FORM_ENUM,
                existing_nullable=False,
            )
            batch_op.drop_column("report_type")


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE TYPE annualreporttype AS ENUM "
            "('individual', 'self_employed', 'company', 'public_institution', 'exempt_dealer')"
        )
        op.execute("ALTER TYPE annualreportform RENAME TO annualreportform_new")
        op.execute("CREATE TYPE annualreportform AS ENUM ('0135', '1301', '1214', '1215', '6111')")
        op.execute(
            """
            ALTER TABLE annual_reports
            ALTER COLUMN form_type TYPE annualreportform
            USING form_type::text::annualreportform
            """
        )
        with op.batch_alter_table("annual_reports", schema=None) as batch_op:
            batch_op.add_column(sa.Column("report_type", _REPORT_TYPE_ENUM, nullable=True))
        op.execute(_DOWNGRADE_REPORT_TYPE_SQL)
        op.execute("ALTER TABLE annual_reports ALTER COLUMN report_type SET NOT NULL")
        op.execute("DROP TYPE annualreportform_new")
    else:
        with op.batch_alter_table("annual_reports", schema=None) as batch_op:
            batch_op.add_column(sa.Column("report_type", _REPORT_TYPE_ENUM, nullable=True))
            batch_op.alter_column(
                "form_type",
                existing_type=_NEW_FORM_ENUM,
                type_=_OLD_FORM_ENUM,
                existing_nullable=False,
            )
        op.execute(_DOWNGRADE_REPORT_TYPE_SQL)
        with op.batch_alter_table("annual_reports", schema=None) as batch_op:
            batch_op.alter_column(
                "report_type",
                existing_type=_REPORT_TYPE_ENUM,
                nullable=False,
            )
