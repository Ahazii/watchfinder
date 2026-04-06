from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
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
    reference_url: str | None = None
    spec_case_material: str | None = None
    spec_bezel: str | None = None
    spec_crystal: str | None = None
    spec_case_back: str | None = None
    spec_case_diameter_mm: Decimal | None = None
    spec_case_height_mm: Decimal | None = None
    spec_lug_width_mm: Decimal | None = None
    spec_water_resistance_m: Decimal | None = None
    spec_dial_color: str | None = None
    spec_dial_material: str | None = None
    spec_indexes_hands: str | None = None
    external_price_history: dict[str, Any] | None = None
    watchbase_imported_at: datetime | None = None
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
    reference_url: str | None = None
    spec_case_material: str | None = None
    spec_bezel: str | None = None
    spec_crystal: str | None = None
    spec_case_back: str | None = None
    spec_case_diameter_mm: Decimal | None = None
    spec_case_height_mm: Decimal | None = None
    spec_lug_width_mm: Decimal | None = None
    spec_water_resistance_m: Decimal | None = None
    spec_dial_color: str | None = None
    spec_dial_material: str | None = None
    spec_indexes_hands: str | None = None


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
    reference_url: str | None = None
    spec_case_material: str | None = None
    spec_bezel: str | None = None
    spec_crystal: str | None = None
    spec_case_back: str | None = None
    spec_case_diameter_mm: Decimal | None = None
    spec_case_height_mm: Decimal | None = None
    spec_lug_width_mm: Decimal | None = None
    spec_water_resistance_m: Decimal | None = None
    spec_dial_color: str | None = None
    spec_dial_material: str | None = None
    spec_indexes_hands: str | None = None


class WatchModelListResponse(BaseModel):
    items: list[WatchModelOut]
    total: int
    skip: int
    limit: int


class PromoteWatchCatalogResponse(BaseModel):
    """Result of POST /api/listings/{id}/promote-watch-catalog."""

    outcome: str
    watch_model: WatchModelOut | None = None


class WatchBaseImportRequest(BaseModel):
    """Optional body for POST import-watchbase (use unsaved Reference URL from the form)."""

    reference_url: str | None = None


class WatchBaseImportResponse(BaseModel):
    """Result of POST /api/watch-models/{id}/import-watchbase."""

    canonical_url: str
    prices_url: str
    fields_updated: list[str]
    price_points: int


class BackfillWatchCatalogResponse(BaseModel):
    """Result of POST /api/watch-models/backfill-from-listings."""

    scanned: int
    already_linked: int
    linked_existing: int
    created_new: int
    skipped_no_identity: int
    queued_for_review: int = 0
