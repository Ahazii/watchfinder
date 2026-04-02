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
    ingest_queries: list[IngestQueryOut]
    env_fallback_query: str
    """Used when no saved lines exist or all are disabled."""
    watch_catalog_review_mode: str = "auto"
    """`auto` = fuzzy match + auto-create catalog rows. `review` = exact match only; queue the rest."""


class SettingsPatch(BaseModel):
    ingest_interval_minutes: int | None = Field(None, ge=5, le=1440)
    ingest_queries: list[IngestQueryIn] | None = None
    watch_catalog_review_mode: str | None = Field(
        None,
        description="auto or review",
    )


class IngestRunResponse(BaseModel):
    status: str
    message: str
