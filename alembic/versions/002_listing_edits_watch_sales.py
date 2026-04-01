"""listing edits + internal watch sale comp database

Revision ID: 002_listing_edits
Revises: 001_initial
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_listing_edits"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listing_edits",
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_family", sa.Text(), nullable=True),
        sa.Column("model_family_source", sa.CHAR(length=1), nullable=True),
        sa.Column("reference_text", sa.Text(), nullable=True),
        sa.Column("reference_source", sa.CHAR(length=1), nullable=True),
        sa.Column("caliber_text", sa.Text(), nullable=True),
        sa.Column("caliber_source", sa.CHAR(length=1), nullable=True),
        sa.Column("repair_supplement", sa.Numeric(12, 2), nullable=True),
        sa.Column("repair_supplement_source", sa.CHAR(length=1), nullable=True),
        sa.Column("donor_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("donor_source", sa.CHAR(length=1), nullable=True),
        sa.Column("recorded_sale_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("recorded_sale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_sale_source", sa.CHAR(length=1), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("listing_id"),
    )

    op.create_table(
        "watch_sale_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ebay_item_id", sa.String(length=32), nullable=False),
        sa.Column("brand_key", sa.String(length=128), nullable=False),
        sa.Column("model_family_key", sa.String(length=256), nullable=True),
        sa.Column("reference_key", sa.String(length=64), nullable=True),
        sa.Column("caliber_key", sa.String(length=128), nullable=True),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source", sa.CHAR(length=1), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_watch_sale_records_brand_key", "watch_sale_records", ["brand_key"]
    )
    op.create_index(
        "ix_watch_sale_records_listing_id", "watch_sale_records", ["listing_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_watch_sale_records_listing_id", table_name="watch_sale_records")
    op.drop_index("ix_watch_sale_records_brand_key", table_name="watch_sale_records")
    op.drop_table("watch_sale_records")
    op.drop_table("listing_edits")
