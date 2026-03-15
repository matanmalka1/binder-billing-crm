"""extend permanent documents

Revision ID: 0021_extend_permanent_documents
Revises: 0020_add_severity_is_read_to_notifications
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = "0021_extend_permanent_documents"
down_revision = "0020_add_severity_is_read_to_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("permanent_documents", schema=None) as batch_op:
        batch_op.alter_column(
            "document_type",
            existing_type=sa.Enum(
                "id_copy", "power_of_attorney", "engagement_agreement", name="documenttype"
            ),
            type_=sa.String(),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("superseded_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(), nullable=False, server_default="pending"))
        batch_op.add_column(sa.Column("annual_report_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("original_filename", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("mime_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("notes", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("approved_by", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))

    op.create_index(
        "ix_permanent_documents_client_type_year",
        "permanent_documents",
        ["client_id", "document_type", "tax_year"],
    )


def downgrade() -> None:
    op.drop_index("ix_permanent_documents_client_type_year", table_name="permanent_documents")

    with op.batch_alter_table("permanent_documents", schema=None) as batch_op:
        batch_op.drop_column("approved_at")
        batch_op.drop_column("approved_by")
        batch_op.drop_column("notes")
        batch_op.drop_column("mime_type")
        batch_op.drop_column("file_size_bytes")
        batch_op.drop_column("original_filename")
        batch_op.drop_column("annual_report_id")
        batch_op.drop_column("status")
        batch_op.drop_column("superseded_by")
        batch_op.drop_column("version")
        batch_op.alter_column(
            "document_type",
            existing_type=sa.String(),
            type_=sa.Enum(
                "id_copy", "power_of_attorney", "engagement_agreement", name="documenttype"
            ),
            existing_nullable=False,
        )
