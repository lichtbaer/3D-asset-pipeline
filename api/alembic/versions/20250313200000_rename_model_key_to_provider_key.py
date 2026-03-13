"""Rename model_key to provider_key in generation_job

Revision ID: 20250313200000
Revises: 20250313100000
Create Date: 2025-03-13

Alte Spalte model_key bleibt als nullable Alias erhalten bis alle Clients migriert sind.
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
    # 1. Neue Spalte provider_key hinzufügen
    op.add_column(
        "generation_job",
        sa.Column("provider_key", sa.String(100), nullable=True),
    )
    # 2. Bestehende Daten kopieren
    op.execute(
        "UPDATE generation_job SET provider_key = model_key WHERE provider_key IS NULL"
    )
    # 3. provider_key NOT NULL machen
    op.alter_column(
        "generation_job",
        "provider_key",
        existing_type=sa.String(100),
        nullable=False,
    )
    # 4. model_key nullable machen (Alias für Rückwärtskompatibilität)
    op.alter_column(
        "generation_job",
        "model_key",
        existing_type=sa.String(100),
        nullable=True,
    )


def downgrade() -> None:
    # 1. model_key wieder NOT NULL (nur wenn alle Zeilen Werte haben)
    op.execute(
        "UPDATE generation_job SET model_key = provider_key WHERE model_key IS NULL"
    )
    op.alter_column(
        "generation_job",
        "model_key",
        existing_type=sa.String(100),
        nullable=False,
    )
    # 2. provider_key Spalte entfernen
    op.drop_column("generation_job", "provider_key")
