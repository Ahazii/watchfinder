from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from watchfinder.schemas.watch_models import WatchModelOut


class WatchLinkReviewBriefOut(BaseModel):
    id: UUID
    tier: str | None = None
    confidence: Decimal | None = None
    candidate_count: int = 0
    reason_codes: list[str] | None = None


class WatchLinkReviewListItem(BaseModel):
    id: UUID
    listing_id: UUID
    ebay_item_id: str
    listing_title: str | None = None
    tier: str | None = None
    confidence: Decimal | None = None
    candidate_count: int = 0
    reason_codes: list[str] | None = None
    created_at: datetime | None = None


class WatchLinkReviewDetailOut(BaseModel):
    id: UUID
    listing_id: UUID
    ebay_item_id: str
    listing_title: str | None = None
    listing_web_url: str | None = None
    tier: str | None = None
    confidence: Decimal | None = None
    reason_codes: list[str] | None = None
    candidate_watch_models: list[WatchModelOut] = Field(default_factory=list)
    candidate_scores: dict[str, float] = Field(default_factory=dict)
    created_at: datetime | None = None


class WatchLinkReviewListResponse(BaseModel):
    items: list[WatchLinkReviewListItem]
    total: int


class ResolveWatchLinkReviewBody(BaseModel):
    action: str = Field(..., description="match | create | dismiss")
    watch_model_id: UUID | None = None


class ResolveWatchLinkReviewResponse(BaseModel):
    status: str
    listing_id: UUID
    watch_model_id: UUID | None = None
