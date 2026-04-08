"""Optional Everywatch watch detail URL (exact listing page for snapshots / search)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "009_everywatch_url"
down_revision = "008_market_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watch_models",
        sa.Column("everywatch_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("watch_models", "everywatch_url")
