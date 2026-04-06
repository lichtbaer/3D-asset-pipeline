"""Add indexes and status check constraint to generation_job

Revision ID: 20260406000000
Revises: 20260325120000
Create Date: 2026-04-06

- Index auf job_type + status (häufigste kombinierte Abfrage)
- Index auf asset_id (FK-ähnliche Lookups)
- CHECK-Constraint auf status (nur gültige Werte erlaubt)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260406000000"
down_revision: Union[str, None] = "20260325120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VALID_STATUSES = ("pending", "processing", "done", "failed")


def upgrade() -> None:
    op.create_index(
        "ix_generation_job_type_status",
        "generation_job",
        ["job_type", "status"],
        unique=False,
    )
    op.create_index(
        "ix_generation_job_asset_id",
        "generation_job",
        ["asset_id"],
        unique=False,
        postgresql_where=sa.text("asset_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_generation_job_status",
        "generation_job",
        sa.text("status IN ('pending', 'processing', 'done', 'failed')"),
    )


def downgrade() -> None:
    op.drop_constraint("ck_generation_job_status", "generation_job", type_="check")
    op.drop_index("ix_generation_job_asset_id", table_name="generation_job")
    op.drop_index("ix_generation_job_type_status", table_name="generation_job")
