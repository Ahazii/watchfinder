from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class IngestQueryOut(BaseModel):
    id: uuid.UUID
    label: str
    query: str
    enabled: bool


class IngestQueryIn(BaseModel):
    label: str = ""
    query: str = Field(..., min_length=1, max_length=2000)
    enabled: bool = True


class SettingsOut(BaseModel):
    ingest_interval_minutes: int
    ebay_search_limit: int
    ingest_max_pages: int = 1
    """Browse search pages per query line (offset steps of search limit)."""
    ingest_queries: list[IngestQueryOut]
    env_fallback_query: str
    """Used when no saved lines exist or all are disabled."""
    watch_catalog_review_mode: str = "auto"
    """`auto` = fuzzy match + auto-create catalog rows. `review` = exact match only; queue the rest."""
    stale_listing_refresh_enabled: bool = False
    stale_listing_refresh_interval_minutes: int = 360
    stale_listing_refresh_max_per_run: int = 20
    stale_listing_refresh_min_age_hours: int = 12
    match_queue_sync_interval_minutes: int = 60
    """0 = do not run scheduled sync; otherwise minutes between unmatched-listing → queue passes."""
    watch_catalog_queue_require_identity: bool = True
    """If true, queue requires brand + (reference or family); if false, queue identity-poor rows too."""
    watch_catalog_excluded_brands: str = ""
    """Comma-separated brands from Settings UI; merged with env WATCH_CATALOG_EXCLUDED_BRANDS."""
    everywatch_login_email: str = ""
    everywatch_password_configured: bool = False
    """Password is never returned; only whether one is stored."""


class SettingsPatch(BaseModel):
    ingest_interval_minutes: int | None = Field(None, ge=5, le=1440)
    ebay_search_limit: int | None = Field(
        None,
        ge=1,
        le=200,
        description="Browse item_summary/search page size per query line (eBay max 200)",
    )
    ingest_max_pages: int | None = Field(
        None,
        ge=1,
        le=20,
        description="How many search result pages to fetch per query line",
    )
    ingest_queries: list[IngestQueryIn] | None = None
    watch_catalog_review_mode: str | None = Field(
        None,
        description="auto or review",
    )
    stale_listing_refresh_enabled: bool | None = None
    stale_listing_refresh_interval_minutes: int | None = Field(None, ge=15, le=1440)
    stale_listing_refresh_max_per_run: int | None = Field(None, ge=1, le=100)
    stale_listing_refresh_min_age_hours: int | None = Field(
        None,
        ge=0,
        le=720,
        description="0 = eligible if last_seen_at is null or strictly before now",
    )
    match_queue_sync_interval_minutes: int | None = Field(
        None,
        ge=0,
        le=1440,
        description="0 = disable scheduled job; 15–1440 = minutes between runs",
    )
    watch_catalog_queue_require_identity: bool | None = Field(
        None,
        description="When true, queue requires brand + reference/family; when false, queue may include low-identity rows",
    )
    watch_catalog_excluded_brands: str | None = Field(
        None,
        max_length=4000,
        description="Comma-separated brand names; merged with env WATCH_CATALOG_EXCLUDED_BRANDS",
    )
    everywatch_login_email: str | None = Field(None, max_length=320)
    everywatch_login_password: str | None = Field(
        None,
        max_length=2000,
        description="Set to update; empty string clears stored password",
    )


class IngestRunResponse(BaseModel):
    status: str
    message: str


class ActiveRefreshStatusResponse(BaseModel):
    running: bool
    total: int = 0
    processed: int = 0
    updated: int = 0
    ended: int = 0
    errors: int = 0
    current_item_id: str | None = None
    current_index: int = 0
    last_status: str | None = None
    last_error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
