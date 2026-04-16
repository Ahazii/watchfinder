"""Add listing_type_source for auto vs manual classification.

Revision ID: 013_listing_type_source
Revises: 012_listing_type
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_listing_type_source"
down_revision: Union[str, None] = "012_listing_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column(
            "listing_type_source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'auto'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("listings", "listing_type_source")
