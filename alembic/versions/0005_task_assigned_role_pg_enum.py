"""alter task assigned_role from String(50) to userrole pg enum

Revision ID: 0005_task_assigned_role_pg_enum
Revises: 0004_task_due_date_to_date
Create Date: 2026-05-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_task_assigned_role_pg_enum"
down_revision: Union[str, None] = "0004_task_due_date_to_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "tasks",
        "assigned_role",
        type_=sa.Enum("advisor", "secretary", name="userrole"),
        existing_type=sa.String(50),
        existing_nullable=True,
        postgresql_using="assigned_role::userrole",
    )


def downgrade() -> None:
    op.alter_column(
        "tasks",
        "assigned_role",
        type_=sa.String(50),
        existing_type=sa.Enum("advisor", "secretary", name="userrole"),
        existing_nullable=True,
        postgresql_using="assigned_role::text",
    )
