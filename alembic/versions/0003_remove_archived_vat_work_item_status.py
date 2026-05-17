"""Remove archived VAT work item status."""

import sqlalchemy as sa
from alembic import op

revision = "0003_remove_archived_vat_work_item_status"
down_revision = "0002_advance_payment_calculation_fields"
branch_labels = None
depends_on = None


VAT_STATUS_VALUES = (
    "pending_materials",
    "material_received",
    "data_entry_in_progress",
    "ready_for_review",
    "filed",
    "canceled",
)

VAT_STATUS_VALUES_WITH_ARCHIVED = (*VAT_STATUS_VALUES, "archived")


def _enum_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE vat_work_items SET status = 'canceled' WHERE status = 'archived'"
        )
    )
    op.execute(sa.text("ALTER TYPE vatworkitemstatus RENAME TO vatworkitemstatus_old"))
    op.execute(
        sa.text(
            f"CREATE TYPE vatworkitemstatus AS ENUM "
            f"({_enum_values(VAT_STATUS_VALUES)})"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE vat_work_items
            ALTER COLUMN status TYPE vatworkitemstatus
            USING status::text::vatworkitemstatus
            """
        )
    )
    op.execute(sa.text("DROP TYPE vatworkitemstatus_old"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TYPE vatworkitemstatus RENAME TO vatworkitemstatus_old"))
    op.execute(
        sa.text(
            f"CREATE TYPE vatworkitemstatus AS ENUM "
            f"({_enum_values(VAT_STATUS_VALUES_WITH_ARCHIVED)})"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE vat_work_items
            ALTER COLUMN status TYPE vatworkitemstatus
            USING status::text::vatworkitemstatus
            """
        )
    )
    op.execute(sa.text("DROP TYPE vatworkitemstatus_old"))
