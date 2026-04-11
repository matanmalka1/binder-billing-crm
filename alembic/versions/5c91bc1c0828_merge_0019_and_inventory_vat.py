"""merge_0019_and_inventory_vat

Revision ID: 5c91bc1c0828
Revises: 0019_reminder_add_client_id_nullable_business, a6b7c8d9e0f1
Create Date: 2026-04-11 13:48:01.516382

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c91bc1c0828'
down_revision: Union[str, Sequence[str], None] = ('0019_reminder_add_client_id_nullable_business', 'a6b7c8d9e0f1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
