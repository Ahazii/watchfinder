from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ParsedAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value_text: str | None


class RepairSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_type: str
    matched_text: str | None
    source_field: str | None


class OpportunityScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estimated_resale: Decimal | None = None
    estimated_repair_cost: Decimal | None = None
    advised_max_buy: Decimal | None = None
    potential_profit: Decimal | None = None
    confidence: Decimal | None = None
    risk: Decimal | None = None
    explanations: list[str] | None = None
    computed_at: datetime | None = None


class ListingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ebay_item_id: str
    title: str | None
    current_price: Decimal | None
    currency: str | None
    web_url: str | None
    condition_description: str | None
    last_seen_at: datetime | None
    score: OpportunityScoreOut | None = None


class ListingDetail(ListingSummary):
    subtitle: str | None = None
    image_urls: list | None = None
    shipping_price: Decimal | None = None
    seller_username: str | None = None
    category_path: str | None = None
    first_seen_at: datetime | None = None
    is_active: bool = True
    parsed_attributes: list[ParsedAttributeOut] = Field(default_factory=list)
    repair_signals: list[RepairSignalOut] = Field(default_factory=list)
    opportunity_scores: list[OpportunityScoreOut] = Field(default_factory=list)


class ListingListResponse(BaseModel):
    items: list[ListingSummary]
    total: int
    skip: int
    limit: int


class DashboardStats(BaseModel):
    total_listings: int
    active_listings: int
    candidate_count: int
    listings_with_repair_signals: int
    recent_listings: list[ListingSummary]
