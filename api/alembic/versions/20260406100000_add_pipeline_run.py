"""Add pipeline_run table für persistierten Pipeline-Status

Revision ID: 20260406100000
Revises: 20260406000000
Create Date: 2026-04-06

Ersetzt den In-Memory-Store in pipeline_orchestrator.py durch eine
persistente DB-Tabelle. Pipeline-Status überlebt API-Neustarts.
TTL-Cleanup (z.B. 30 Tage) über periodischen Job oder Startup-Hook.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "20260406100000"
down_revision: Union[str, None] = "20260406000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("steps", JSONB(astext_type=sa.Text()), nullable=False),
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
    op.create_index("ix_pipeline_run_status", "pipeline_run", ["status"])
    op.create_index("ix_pipeline_run_created_at", "pipeline_run", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_created_at", table_name="pipeline_run")
    op.drop_index("ix_pipeline_run_status", table_name="pipeline_run")
    op.drop_table("pipeline_run")
