from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WatchModelBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand: str
    model_family: str | None = None
    model_name: str | None = None
    reference: str | None = None
    observed_price_low: Decimal | None = None
    observed_price_high: Decimal | None = None
    manual_price_low: Decimal | None = None
    manual_price_high: Decimal | None = None


class WatchModelOut(WatchModelBriefOut):
    caliber: str | None = None
    image_urls: list[str] | None = None
    production_start: date | None = None
    production_end: date | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WatchModelCreate(BaseModel):
    brand: str = Field(..., min_length=1, max_length=255)
    model_family: str | None = None
    model_name: str | None = None
    reference: str | None = Field(None, max_length=128)
    caliber: str | None = None
    image_urls: list[str] | None = None
    production_start: date | None = None
    production_end: date | None = None
    description: str | None = None
    manual_price_low: Decimal | None = None
    manual_price_high: Decimal | None = None


class WatchModelPatch(BaseModel):
    brand: str | None = Field(None, min_length=1, max_length=255)
    model_family: str | None = None
    model_name: str | None = None
    reference: str | None = Field(None, max_length=128)
    caliber: str | None = None
    image_urls: list[str] | None = None
    production_start: date | None = None
    production_end: date | None = None
    description: str | None = None
    manual_price_low: Decimal | None = None
    manual_price_high: Decimal | None = None


class WatchModelListResponse(BaseModel):
    items: list[WatchModelOut]
    total: int
    skip: int
    limit: int


class PromoteWatchCatalogResponse(BaseModel):
    """Result of POST /api/listings/{id}/promote-watch-catalog."""

    outcome: str
    watch_model: WatchModelOut | None = None


class BackfillWatchCatalogResponse(BaseModel):
    """Result of POST /api/watch-models/backfill-from-listings."""

    scanned: int
    already_linked: int
    linked_existing: int
    created_new: int
    skipped_no_identity: int
    queued_for_review: int = 0
