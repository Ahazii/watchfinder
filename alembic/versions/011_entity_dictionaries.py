"""Brands, calibers, stock references + listing resolution FKs.

Revision ID: 011_entity_dictionaries
Revises: 010_not_interested_listings
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_entity_dictionaries"
down_revision: Union[str, None] = "010_not_interested_listings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=False),
        sa.Column("norm_key", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("norm_key", name="uq_brands_norm_key"),
    )
    op.create_index("ix_brands_display_name", "brands", ["display_name"], unique=False)

    op.create_table(
        "calibers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_text", sa.Text(), nullable=False),
        sa.Column("norm_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calibers_norm_key", "calibers", ["norm_key"], unique=False)

    op.create_table(
        "stock_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ref_text", sa.Text(), nullable=False),
        sa.Column("norm_key", sa.Text(), nullable=False),
        sa.Column("watch_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["watch_model_id"], ["watch_models.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "norm_key", name="uq_stock_references_brand_norm"),
    )
    op.create_index(
        "ix_stock_references_brand_id", "stock_references", ["brand_id"], unique=False
    )

    op.create_table(
        "caliber_brand_links",
        sa.Column("caliber_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["caliber_id"], ["calibers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("caliber_id", "brand_id"),
    )

    op.create_table(
        "caliber_stock_reference_links",
        sa.Column("caliber_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_reference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["caliber_id"], ["calibers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["stock_reference_id"], ["stock_references.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("caliber_id", "stock_reference_id"),
    )

    op.add_column(
        "listings",
        sa.Column("resolved_brand_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("resolved_stock_reference_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_listings_resolved_brand_id",
        "listings",
        "brands",
        ["resolved_brand_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_listings_resolved_stock_reference_id",
        "listings",
        "stock_references",
        ["resolved_stock_reference_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_listings_resolved_brand_id", "listings", ["resolved_brand_id"])
    op.create_index(
        "ix_listings_resolved_stock_reference_id",
        "listings",
        ["resolved_stock_reference_id"],
    )

    op.create_table(
        "listing_calibers",
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("caliber_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["caliber_id"], ["calibers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("listing_id", "caliber_id"),
    )


def downgrade() -> None:
    op.drop_table("listing_calibers")
    op.drop_index("ix_listings_resolved_stock_reference_id", table_name="listings")
    op.drop_index("ix_listings_resolved_brand_id", table_name="listings")
    op.drop_constraint("fk_listings_resolved_stock_reference_id", "listings", type_="foreignkey")
    op.drop_constraint("fk_listings_resolved_brand_id", "listings", type_="foreignkey")
    op.drop_column("listings", "resolved_stock_reference_id")
    op.drop_column("listings", "resolved_brand_id")
    op.drop_table("caliber_stock_reference_links")
    op.drop_table("caliber_brand_links")
    op.drop_index("ix_stock_references_brand_id", table_name="stock_references")
    op.drop_table("stock_references")
    op.drop_index("ix_calibers_norm_key", table_name="calibers")
    op.drop_table("calibers")
    op.drop_index("ix_brands_display_name", table_name="brands")
    op.drop_table("brands")
