"""Widen ebay_item_id for REST item ids (e.g. v1|...|0)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "005_ebay_item_id_length"
down_revision = "004_watch_link_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "listings",
        "ebay_item_id",
        existing_type=sa.String(length=32),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
    op.alter_column(
        "watch_sale_records",
        "ebay_item_id",
        existing_type=sa.String(length=32),
        type_=sa.String(length=128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "watch_sale_records",
        "ebay_item_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.alter_column(
        "listings",
        "ebay_item_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
