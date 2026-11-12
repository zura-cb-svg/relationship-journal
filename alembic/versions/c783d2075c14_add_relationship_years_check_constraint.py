"""add relationship years check constraint

Revision ID: c783d2075c14
Revises: f63af230d5ae
Create Date: 2026-11-11 11:16:39.446729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c783d2075c14'
down_revision: Union[str, Sequence[str], None] = 'f63af230d5ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_relationships_years_together_nonnegative",
        "relationships",
        "years_together >= 0" )
    

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_relationships_years_together_nonnegative",
        "relationships",
        type_="check"
    )
