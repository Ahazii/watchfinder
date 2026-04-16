"""Add listing_type to listings.

Revision ID: 012_listing_type
Revises: 011_entity_dictionaries
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_listing_type"
down_revision: Union[str, None] = "011_entity_dictionaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column(
            "listing_type",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("listings", "listing_type")
