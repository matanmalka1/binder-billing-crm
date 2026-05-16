"""remove signature request draft status

Revision ID: 0007_remove_signature_request_draft
Revises: 0006_simplify_annual_report_statuses
Create Date: 2026-05-15 00:00:00.000000

Run:
- Upgrade:   APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic upgrade 0007_remove_signature_request_draft
- Downgrade: APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic downgrade 0006_simplify_annual_report_statuses

Notes:
- Signature requests no longer support a draft state.
- Existing draft rows cannot be made signable safely because they have no issued token,
  so they are converted to canceled before shrinking the PostgreSQL enum.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007_remove_signature_request_draft"
down_revision: Union[str, Sequence[str], None] = "0006_simplify_annual_report_statuses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_VALUES = (
    "draft",
    "pending_signature",
    "signed",
    "declined",
    "expired",
    "canceled",
)
NEW_VALUES = (
    "pending_signature",
    "signed",
    "declined",
    "expired",
    "canceled",
)


def _cancel_draft_requests() -> None:
    op.execute(
        sa.text(
            """
            UPDATE signature_requests
            SET status = 'canceled',
                signing_token = NULL,
                canceled_at = COALESCE(canceled_at, CURRENT_TIMESTAMP),
                expiry_days = COALESCE(expiry_days, 14)
            WHERE CAST(status AS TEXT) = 'draft'
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    _cancel_draft_requests()

    if bind.dialect.name == "postgresql":
        # The initial schema had no database default for this column.
        # Keep it that way: a pending request is valid only with token/expiry fields.
        op.execute(
            sa.text("ALTER TABLE signature_requests ALTER COLUMN status DROP DEFAULT")
        )
        op.execute(
            sa.text(
                "ALTER TYPE signaturerequeststatus RENAME TO signaturerequeststatus_old"
            )
        )
        new_enum = postgresql.ENUM(*NEW_VALUES, name="signaturerequeststatus")
        new_enum.create(bind, checkfirst=False)
        op.alter_column(
            "signature_requests",
            "status",
            type_=new_enum,
            existing_type=postgresql.ENUM(
                *OLD_VALUES, name="signaturerequeststatus_old"
            ),
            existing_nullable=False,
            postgresql_using="status::text::signaturerequeststatus",
        )
        op.execute(sa.text("DROP TYPE signaturerequeststatus_old"))
        return

    with op.batch_alter_table("signature_requests") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(*OLD_VALUES, name="signaturerequeststatus"),
            type_=sa.Enum(*NEW_VALUES, name="signaturerequeststatus"),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TYPE signaturerequeststatus RENAME TO signaturerequeststatus_new"
            )
        )
        old_enum = postgresql.ENUM(*OLD_VALUES, name="signaturerequeststatus")
        old_enum.create(bind, checkfirst=False)
        op.alter_column(
            "signature_requests",
            "status",
            type_=old_enum,
            existing_type=postgresql.ENUM(
                *NEW_VALUES, name="signaturerequeststatus_new"
            ),
            existing_nullable=False,
            postgresql_using="status::text::signaturerequeststatus",
        )
        op.execute(sa.text("DROP TYPE signaturerequeststatus_new"))
        return

    with op.batch_alter_table("signature_requests") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(*NEW_VALUES, name="signaturerequeststatus"),
            type_=sa.Enum(*OLD_VALUES, name="signaturerequeststatus"),
            existing_nullable=False,
        )
