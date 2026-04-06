"""WatchBase on-demand import: price history JSON + import timestamp."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "007_watchbase_import"
down_revision = "006_watch_model_specs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watch_models",
        sa.Column("external_price_history", JSONB, nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column(
            "watchbase_imported_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("watch_models", "watchbase_imported_at")
    op.drop_column("watch_models", "external_price_history")
