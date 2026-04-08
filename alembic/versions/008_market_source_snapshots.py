"""Chrono24 / Everywatch-style market snapshot JSON (optional auto + manual refresh)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "008_market_snapshots"
down_revision = "007_watchbase_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watch_models",
        sa.Column("market_source_snapshots", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("watch_models", "market_source_snapshots")
