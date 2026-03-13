"""Add error_type and error_detail to generation_job

Revision ID: 20250313400000
Revises: 20250313300000
Create Date: 2025-03-13

Strukturierter Fehlerkontext bei Job-Failure: error_type (Klassenname),
error_detail (str(exception)). Migration reversibel.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250313400000"
down_revision: Union[str, None] = "20250313300000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_job",
        sa.Column("error_type", sa.String(100), nullable=True),
    )
    op.add_column(
        "generation_job",
        sa.Column("error_detail", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_job", "error_detail")
    op.drop_column("generation_job", "error_type")
