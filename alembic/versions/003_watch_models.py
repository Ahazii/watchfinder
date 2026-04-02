"""watch_models catalog + listings.watch_model_id

Revision ID: 003_watch_models
Revises: 002_listing_edits
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_watch_models"
down_revision: Union[str, None] = "002_listing_edits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watch_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("model_family", sa.Text(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("caliber", sa.Text(), nullable=True),
        sa.Column("image_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("production_start", sa.Date(), nullable=True),
        sa.Column("production_end", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manual_price_low", sa.Numeric(12, 2), nullable=True),
        sa.Column("manual_price_high", sa.Numeric(12, 2), nullable=True),
        sa.Column("observed_price_low", sa.Numeric(12, 2), nullable=True),
        sa.Column("observed_price_high", sa.Numeric(12, 2), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watch_models_brand", "watch_models", ["brand"])
    op.create_index("ix_watch_models_reference", "watch_models", ["reference"])

    op.add_column(
        "listings",
        sa.Column(
            "watch_model_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_listings_watch_model_id",
        "listings",
        "watch_models",
        ["watch_model_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_listings_watch_model_id", "listings", ["watch_model_id"])

    op.execute(
        """
        CREATE UNIQUE INDEX uq_watch_models_brand_ref_lower
        ON watch_models (
            lower(trim(brand)),
            lower(trim(reference))
        )
        WHERE reference IS NOT NULL AND btrim(reference) <> '';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_watch_models_brand_ref_lower")
    op.drop_index("ix_listings_watch_model_id", table_name="listings")
    op.drop_constraint("fk_listings_watch_model_id", "listings", type_="foreignkey")
    op.drop_column("listings", "watch_model_id")
    op.drop_index("ix_watch_models_reference", table_name="watch_models")
    op.drop_index("ix_watch_models_brand", table_name="watch_models")
    op.drop_table("watch_models")
