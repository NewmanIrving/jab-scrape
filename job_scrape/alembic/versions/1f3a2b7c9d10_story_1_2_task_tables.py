"""story 1.2 task tables

Revision ID: 1f3a2b7c9d10
Revises: 51aa0ae6bba7
Create Date: 2026-03-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f3a2b7c9d10"
down_revision: Union[str, Sequence[str], None] = "51aa0ae6bba7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("customer_scope", sa.JSON(), nullable=False),
        sa.Column("triggered_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'success', 'failed', 'manual')",
            name="ck_tasks_status_valid",
        ),
        sa.UniqueConstraint("task_id"),
    )
    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"]),
    )
    op.create_index(
        op.f("ix_task_events_task_id"), "task_events", ["task_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_task_events_task_id"), table_name="task_events")
    op.drop_table("task_events")
    op.drop_table("tasks")
