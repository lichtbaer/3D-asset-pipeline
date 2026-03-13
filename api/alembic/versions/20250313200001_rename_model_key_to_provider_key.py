"""Rename model_key to provider_key in generation_job

Revision ID: 20250313200001
Revises: 20250313200000
Create Date: 2025-03-13

Läuft nach add_provider_key (main). Macht provider_key zur Hauptspalte,
model_key bleibt als nullable Alias erhalten.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250313200001"
down_revision: Union[str, None] = "20250313200000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # provider_key wurde bereits von 20250313200000 hinzugefügt (nullable)
    # 1. Bestehende Daten kopieren (model_key → provider_key wo NULL)
    op.execute(
        "UPDATE generation_job SET provider_key = model_key WHERE provider_key IS NULL"
    )
    # 2. provider_key NOT NULL machen
    op.alter_column(
        "generation_job",
        "provider_key",
        existing_type=sa.String(50),
        nullable=False,
    )
    # 3. model_key nullable machen (Alias für Rückwärtskompatibilität)
    op.alter_column(
        "generation_job",
        "model_key",
        existing_type=sa.String(100),
        nullable=True,
    )


def downgrade() -> None:
    # 1. model_key wieder NOT NULL
    op.execute(
        "UPDATE generation_job SET model_key = provider_key WHERE model_key IS NULL"
    )
    op.alter_column(
        "generation_job",
        "model_key",
        existing_type=sa.String(100),
        nullable=False,
    )
    # 2. provider_key wieder nullable (wie vor dieser Migration)
    op.alter_column(
        "generation_job",
        "provider_key",
        existing_type=sa.String(50),
        nullable=True,
    )
