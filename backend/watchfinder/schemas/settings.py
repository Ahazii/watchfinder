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


class SettingsPatch(BaseModel):
    ingest_interval_minutes: int | None = Field(None, ge=5, le=1440)
    ingest_queries: list[IngestQueryIn] | None = None


class IngestRunResponse(BaseModel):
    status: str
    message: str
