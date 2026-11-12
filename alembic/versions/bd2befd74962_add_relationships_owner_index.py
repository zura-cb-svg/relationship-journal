"""add relationships owner index

Revision ID: bd2befd74962
Revises: c783d2075c14
Create Date: 2026-11-11 11:43:55.782468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd2befd74962'
down_revision: Union[str, Sequence[str], None] = 'c783d2075c14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_relationships_owner_id", "relationships",	["owner_id"] , unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_relationships_owner_id",table_name="relationships")
