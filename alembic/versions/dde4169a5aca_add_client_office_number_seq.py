"""add client_office_number_seq

Revision ID: dde4169a5aca
Revises: fc1eacc58833
Create Date: 2026-05-10 10:41:36.053855

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "dde4169a5aca"
down_revision: Union[str, Sequence[str], None] = "fc1eacc58833"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        max_num = conn.execute(
            sa.text("SELECT COALESCE(MAX(office_client_number), 0) FROM client_records")
        ).scalar()
        start = (max_num or 0) + 1
        conn.execute(
            sa.text(
                f"CREATE SEQUENCE IF NOT EXISTS client_office_number_seq START WITH {start}"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("DROP SEQUENCE IF EXISTS client_office_number_seq"))
