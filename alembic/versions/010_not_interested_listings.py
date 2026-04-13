"""Add not_interested_listings blocklist table.

Revision ID: 010_not_interested_listings
Revises: 009_everywatch_url
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_not_interested_listings"
down_revision: Union[str, None] = "009_everywatch_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "not_interested_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ebay_item_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("last_listing_title", sa.Text(), nullable=True),
        sa.Column("last_listing_web_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_not_interested_listings_ebay_item_id",
        "not_interested_listings",
        ["ebay_item_id"],
        unique=True,
    )
    op.create_index(
        "ix_not_interested_listings_is_active",
        "not_interested_listings",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_not_interested_listings_is_active", table_name="not_interested_listings")
    op.drop_index("ix_not_interested_listings_ebay_item_id", table_name="not_interested_listings")
    op.drop_table("not_interested_listings")
