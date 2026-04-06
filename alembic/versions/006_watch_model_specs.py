"""Optional watch_specs + reference_url (e.g. manual WatchBase data)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006_watch_model_specs"
down_revision = "005_ebay_item_id_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watch_models",
        sa.Column("reference_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column("spec_case_material", sa.Text(), nullable=True),
    )
    op.add_column("watch_models", sa.Column("spec_bezel", sa.Text(), nullable=True))
    op.add_column("watch_models", sa.Column("spec_crystal", sa.Text(), nullable=True))
    op.add_column("watch_models", sa.Column("spec_case_back", sa.Text(), nullable=True))
    op.add_column(
        "watch_models",
        sa.Column("spec_case_diameter_mm", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column("spec_case_height_mm", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column("spec_lug_width_mm", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column("spec_water_resistance_m", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column("spec_dial_color", sa.Text(), nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column("spec_dial_material", sa.Text(), nullable=True),
    )
    op.add_column(
        "watch_models",
        sa.Column("spec_indexes_hands", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("watch_models", "spec_indexes_hands")
    op.drop_column("watch_models", "spec_dial_material")
    op.drop_column("watch_models", "spec_dial_color")
    op.drop_column("watch_models", "spec_water_resistance_m")
    op.drop_column("watch_models", "spec_lug_width_mm")
    op.drop_column("watch_models", "spec_case_height_mm")
    op.drop_column("watch_models", "spec_case_diameter_mm")
    op.drop_column("watch_models", "spec_case_back")
    op.drop_column("watch_models", "spec_crystal")
    op.drop_column("watch_models", "spec_bezel")
    op.drop_column("watch_models", "spec_case_material")
    op.drop_column("watch_models", "reference_url")
