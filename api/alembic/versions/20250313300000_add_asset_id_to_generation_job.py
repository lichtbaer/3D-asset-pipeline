"""Add asset_id to generation_job

Revision ID: 20250313300000
Revises: 20250313210000
Create Date: 2025-03-13

Asset-Persistenz: asset_id verknüpft Job mit Asset-Ordner (UUID, nullable).
Keine FK auf asset-Tabelle (Assets liegen im Filesystem).
Migration reversibel.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "20250313300000"
down_revision: Union[str, None] = "20250313210000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_job",
        sa.Column("asset_id", UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_job", "asset_id")
