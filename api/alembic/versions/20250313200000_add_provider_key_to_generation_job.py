"""Add provider_key to generation_job

Revision ID: 20250313200000
Revises: 20250313100000
Create Date: 2025-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250313200000"
down_revision: Union[str, None] = "20250313100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_job",
        sa.Column("provider_key", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_job", "provider_key")
