"""baseline

Revision ID: 51aa0ae6bba7
Revises: 
Create Date: 2026-03-13 02:00:42.314088

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '51aa0ae6bba7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
