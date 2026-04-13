from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotInterestedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ebay_item_id: str
    source: str | None = None
    reason: str | None = None
    note: str | None = None
    last_listing_title: str | None = None
    last_listing_web_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    restored_at: datetime | None = None


class NotInterestedListResponse(BaseModel):
    items: list[NotInterestedOut]
    total: int
