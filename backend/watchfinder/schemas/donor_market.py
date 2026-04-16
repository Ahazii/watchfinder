from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DonorMovementBandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str
    sample_count: int
    p25: Decimal | None = None
    median: Decimal | None = None
    p75: Decimal | None = None
    low: Decimal | None = None
    high: Decimal | None = None


class DonorMovementMarketOut(BaseModel):
    """Asking prices on active ingest listings classified movement_only and linked to this caliber."""

    caliber_id: UUID | None = None
    caliber_display_text: str | None = None
    caliber_norm_key: str | None = None
    listing_type: str = Field(default="movement_only", description="Filter on listings.listing_type")
    total_samples: int = 0
    bands: list[DonorMovementBandOut] = Field(default_factory=list)
    match_note: str | None = Field(
        None,
        description="How caliber was resolved (watch model route) or None (direct caliber id)",
    )
