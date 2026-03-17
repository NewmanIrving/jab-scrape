"""story 3.2 add lifecycle seen fields to raw_job_postings

Revision ID: a9b8c7d6e5f4
Revises: f1b2c3d4e5a6
Create Date: 2026-03-17 15:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "f1b2c3d4e5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "raw_job_postings",
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "raw_job_postings",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "raw_job_postings",
        sa.Column("times_seen", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_raw_job_postings_platform_source_job_id",
        "raw_job_postings",
        ["source_platform", "source_job_id"],
    )
    op.create_index(
        "ix_raw_job_postings_platform_source_url_canonical",
        "raw_job_postings",
        ["source_platform", "source_url_canonical"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_raw_job_postings_platform_source_url_canonical",
        table_name="raw_job_postings",
    )
    op.drop_index(
        "ix_raw_job_postings_platform_source_job_id",
        table_name="raw_job_postings",
    )

    op.drop_column("raw_job_postings", "times_seen")
    op.drop_column("raw_job_postings", "last_seen_at")
    op.drop_column("raw_job_postings", "first_seen_at")
