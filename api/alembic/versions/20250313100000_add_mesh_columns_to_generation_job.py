"""Add mesh columns to generation_job

Revision ID: 20250313100000
Revises: 20250313000000
Create Date: 2025-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250313100000"
down_revision: Union[str, None] = "20250313000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_job",
        sa.Column("source_image_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "generation_job",
        sa.Column(
            "source_job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "generation_job",
        sa.Column("glb_file_path", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_job", "glb_file_path")
    op.drop_column("generation_job", "source_job_id")
    op.drop_column("generation_job", "source_image_url")
