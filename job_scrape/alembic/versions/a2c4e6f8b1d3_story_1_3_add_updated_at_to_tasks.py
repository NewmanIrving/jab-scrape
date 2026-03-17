"""story 1.3 add updated_at to tasks

Revision ID: a2c4e6f8b1d3
Revises: 1f3a2b7c9d10
Create Date: 2026-03-13 12:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c4e6f8b1d3"
down_revision: Union[str, Sequence[str], None] = "1f3a2b7c9d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "updated_at")
