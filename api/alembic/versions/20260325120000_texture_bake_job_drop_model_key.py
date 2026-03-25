"""Texture-Bake-Jobs persistent; generation_job.model_key entfernen

Revision ID: 20260325120000
Revises: 20250313400000
Create Date: 2026-03-25

- Tabelle texture_bake_job fuer asynchrones Texture-Baking (ersetzt In-Memory-Dict).
- Spalte model_key aus generation_job entfernt (nur noch provider_key).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "20260325120000"
down_revision: Union[str, None] = "20250313400000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "texture_bake_job",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("source_mesh", sa.String(512), nullable=False),
        sa.Column("target_mesh", sa.String(512), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("bake_types", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_file", sa.String(512), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_texture_bake_job_asset_id",
        "texture_bake_job",
        ["asset_id"],
        unique=False,
    )
    op.drop_column("generation_job", "model_key")


def downgrade() -> None:
    op.add_column(
        "generation_job",
        sa.Column("model_key", sa.String(100), nullable=True),
    )
    op.execute(
        "UPDATE generation_job SET model_key = provider_key WHERE model_key IS NULL"
    )
    op.drop_index("ix_texture_bake_job_asset_id", table_name="texture_bake_job")
    op.drop_table("texture_bake_job")
