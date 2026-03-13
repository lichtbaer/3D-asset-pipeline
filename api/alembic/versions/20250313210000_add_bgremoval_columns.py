"""Add bgremoval columns to generation_job

Revision ID: 20250313210000
Revises: 20250313200001
Create Date: 2025-03-13

Neue Spalten für Background-Removal: bgremoval_provider_key, bgremoval_result_url.
Migration reversibel.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250313210000"
down_revision: Union[str, None] = "20250313200001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_job",
        sa.Column("bgremoval_provider_key", sa.String(100), nullable=True),
    )
    op.add_column(
        "generation_job",
        sa.Column("bgremoval_result_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_job", "bgremoval_result_url")
    op.drop_column("generation_job", "bgremoval_provider_key")
