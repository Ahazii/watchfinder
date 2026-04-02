"""watch_model_link_reviews queue for manual catalog matching

Revision ID: 004_watch_link_reviews
Revises: 003_watch_models
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_watch_link_reviews"
down_revision: Union[str, None] = "003_watch_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watch_model_link_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("tier", sa.String(length=16), nullable=True),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "candidate_watch_model_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "candidate_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
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
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_watch_model_link_reviews_listing_id",
        "watch_model_link_reviews",
        ["listing_id"],
    )
    op.create_index(
        "ix_watch_model_link_reviews_status",
        "watch_model_link_reviews",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_watch_model_link_reviews_status", table_name="watch_model_link_reviews")
    op.drop_index("ix_watch_model_link_reviews_listing_id", table_name="watch_model_link_reviews")
    op.drop_table("watch_model_link_reviews")
