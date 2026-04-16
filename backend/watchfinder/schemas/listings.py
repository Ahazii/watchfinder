from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from watchfinder.schemas.watch_link_reviews import WatchLinkReviewBriefOut
from watchfinder.schemas.watch_models import WatchModelBriefOut

ListingType = Literal["watch_complete", "movement_only", "parts_other", "unknown"]
ListingTypeSource = Literal["auto", "manual"]


class ValuedStringOut(BaseModel):
    """Value plus provenance letter (M/I/S/R/O/H/P) or empty if none."""

    value: str | None = None
    source: str = ""


class MoneyWithSourceOut(BaseModel):
    amount: Decimal | None = None
    source: str = ""


class RecordedSaleOut(BaseModel):
    price: Decimal | None = None
    recorded_at: datetime | None = None
    source: str = ""


class CompBandOut(BaseModel):
    count: int = 0
    p25: Decimal | None = None
    p75: Decimal | None = None
    low: Decimal | None = None
    high: Decimal | None = None
    label: str = ""


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
    buying_options: list[str] | None = None
    listing_ended_at: datetime | None = None
    last_seen_at: datetime | None
    first_seen_at: datetime | None = None
    is_active: bool = True
    image_urls: list | None = None
    watch_model_id: UUID | None = None
    resolved_brand_id: UUID | None = None
    resolved_stock_reference_id: UUID | None = None
    listing_type: ListingType = "unknown"
    listing_type_source: ListingTypeSource = "auto"
    score: OpportunityScoreOut | None = None


class ListingDetail(ListingSummary):
    subtitle: str | None = None
    shipping_price: Decimal | None = None
    seller_username: str | None = None
    category_path: str | None = None
    first_seen_at: datetime | None = None
    parsed_attributes: list[ParsedAttributeOut] = Field(default_factory=list)
    repair_signals: list[RepairSignalOut] = Field(default_factory=list)
    opportunity_scores: list[OpportunityScoreOut] = Field(default_factory=list)
    # Valuation / edits (detail page)
    brand: ValuedStringOut = Field(default_factory=ValuedStringOut)
    model_family: ValuedStringOut = Field(default_factory=ValuedStringOut)
    reference: ValuedStringOut = Field(default_factory=ValuedStringOut)
    caliber: ValuedStringOut = Field(default_factory=ValuedStringOut)
    repair_supplement: MoneyWithSourceOut = Field(default_factory=MoneyWithSourceOut)
    donor_cost: MoneyWithSourceOut = Field(default_factory=MoneyWithSourceOut)
    recorded_sale: RecordedSaleOut = Field(default_factory=RecordedSaleOut)
    notes: str | None = None
    comp_sales: CompBandOut = Field(default_factory=CompBandOut)
    comp_asking: CompBandOut = Field(default_factory=CompBandOut)
    source_legend: dict[str, str] = Field(default_factory=dict)
    field_guidance: dict[str, str] = Field(default_factory=dict)
    watch_model: WatchModelBriefOut | None = None
    watch_link_review_pending: WatchLinkReviewBriefOut | None = Field(default=None)


class ListingEditsPatch(BaseModel):
    """PATCH body: only include fields you want to change. Use null to clear optional numbers."""

    watch_model_id: UUID | None = None
    model_family: str | None = None
    model_family_source: str | None = Field(None, max_length=1)
    reference_text: str | None = None
    reference_source: str | None = Field(None, max_length=1)
    caliber_text: str | None = None
    caliber_source: str | None = Field(None, max_length=1)
    repair_supplement: Decimal | None = None
    repair_supplement_source: str | None = Field(None, max_length=1)
    donor_cost: Decimal | None = None
    donor_source: str | None = Field(None, max_length=1)
    recorded_sale_price: Decimal | None = None
    recorded_sale_at: datetime | None = None
    recorded_sale_source: str | None = Field(None, max_length=1)
    notes: str | None = None
    listing_type: ListingType | None = None
    listing_type_source: ListingTypeSource | None = None


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
    ebay_browse_search_calls: int = 0
    ebay_oauth_token_calls: int = 0
    ebay_browse_get_item_calls: int = 0
