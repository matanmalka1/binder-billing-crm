"""add_correspondence_entries_table

Revision ID: 0004_add_correspondence_entries_table
Revises: 0003_remove_business_sector
Create Date: 2026-03-05 18:15:52.174717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_add_correspondence_entries_table'
down_revision: Union[str, Sequence[str], None] = '0003_remove_business_sector'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "correspondence_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column(
            "correspondence_type",
            sa.Enum("call", "letter", "email", "meeting", name="correspondencetype"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["authority_contacts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_correspondence_client", "correspondence_entries", ["client_id"])
    op.create_index("idx_correspondence_occurred", "correspondence_entries", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("idx_correspondence_occurred", table_name="correspondence_entries")
    op.drop_index("idx_correspondence_client", table_name="correspondence_entries")
    op.drop_table("correspondence_entries")
