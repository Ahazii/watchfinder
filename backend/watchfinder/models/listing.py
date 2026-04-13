from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from watchfinder.db import Base


class WatchModel(Base):
    """Canonical watch type (many listings can link here). Price bounds: observed auto + manual."""

    __tablename__ = "watch_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand: Mapped[str] = mapped_column(String(255), index=True)
    model_family: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(String(128), index=True)
    caliber: Mapped[str | None] = mapped_column(Text)
    image_urls: Mapped[list | None] = mapped_column(JSONB)
    production_start: Mapped[date | None] = mapped_column(Date)
    production_end: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    manual_price_low: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    manual_price_high: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    observed_price_low: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    observed_price_high: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reference_url: Mapped[str | None] = mapped_column(Text)
    everywatch_url: Mapped[str | None] = mapped_column(Text)
    spec_case_material: Mapped[str | None] = mapped_column(Text)
    spec_bezel: Mapped[str | None] = mapped_column(Text)
    spec_crystal: Mapped[str | None] = mapped_column(Text)
    spec_case_back: Mapped[str | None] = mapped_column(Text)
    spec_case_diameter_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    spec_case_height_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    spec_lug_width_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    spec_water_resistance_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    spec_dial_color: Mapped[str | None] = mapped_column(Text)
    spec_dial_material: Mapped[str | None] = mapped_column(Text)
    spec_indexes_hands: Mapped[str | None] = mapped_column(Text)
    external_price_history: Mapped[dict | None] = mapped_column(JSONB)
    market_source_snapshots: Mapped[dict | None] = mapped_column(JSONB)
    watchbase_imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listings = relationship("Listing", back_populates="watch_model")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ebay_item_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    title: Mapped[str | None] = mapped_column(Text)
    subtitle: Mapped[str | None] = mapped_column(Text)
    web_url: Mapped[str | None] = mapped_column(Text)
    image_urls: Mapped[list | None] = mapped_column(JSONB)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    shipping_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    seller_username: Mapped[str | None] = mapped_column(String(255))
    condition_id: Mapped[str | None] = mapped_column(String(64))
    condition_description: Mapped[str | None] = mapped_column(Text)
    buying_options: Mapped[list | None] = mapped_column(JSONB)
    category_path: Mapped[str | None] = mapped_column(Text)
    listing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    listing_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    item_aspects: Mapped[dict | None] = mapped_column(JSONB)
    raw_item_json: Mapped[dict | None] = mapped_column(JSONB)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    watch_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watch_models.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    snapshots = relationship(
        "ListingSnapshot", back_populates="listing", passive_deletes=True
    )
    parsed_attributes = relationship(
        "ParsedAttribute", back_populates="listing", passive_deletes=True
    )
    repair_signals = relationship(
        "RepairSignal", back_populates="listing", passive_deletes=True
    )
    opportunity_scores = relationship(
        "OpportunityScore", back_populates="listing", passive_deletes=True
    )
    listing_edit = relationship(
        "ListingEdit",
        back_populates="listing",
        uselist=False,
        cascade="all, delete-orphan",
    )
    watch_model = relationship("WatchModel", back_populates="listings")
    watch_link_reviews = relationship(
        "WatchModelLinkReview",
        back_populates="listing",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WatchModelLinkReview(Base):
    """Queue row when watch_catalog_review_mode=review and catalog link needs human decision."""

    __tablename__ = "watch_model_link_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    tier: Mapped[str | None] = mapped_column(String(16))
    reason_codes: Mapped[list | None] = mapped_column(JSONB)
    candidate_watch_model_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    candidate_scores: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    listing = relationship("Listing", back_populates="watch_link_reviews")


class ListingEdit(Base):
    """User overrides and manual valuation fields (sources: M/I/S/R/O/H/P — see README)."""

    __tablename__ = "listing_edits"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True
    )
    model_family: Mapped[str | None] = mapped_column(Text)
    model_family_source: Mapped[str | None] = mapped_column(String(1))
    reference_text: Mapped[str | None] = mapped_column(Text)
    reference_source: Mapped[str | None] = mapped_column(String(1))
    caliber_text: Mapped[str | None] = mapped_column(Text)
    caliber_source: Mapped[str | None] = mapped_column(String(1))
    repair_supplement: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    repair_supplement_source: Mapped[str | None] = mapped_column(String(1))
    donor_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    donor_source: Mapped[str | None] = mapped_column(String(1))
    recorded_sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    recorded_sale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_sale_source: Mapped[str | None] = mapped_column(String(1))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listing = relationship("Listing", back_populates="listing_edit")


class WatchSaleRecord(Base):
    """Internal comp DB: prices we recorded (manual or future ingest-observed)."""

    __tablename__ = "watch_sale_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"), index=True
    )
    ebay_item_id: Mapped[str] = mapped_column(String(128))
    brand_key: Mapped[str] = mapped_column(String(128), index=True)
    model_family_key: Mapped[str | None] = mapped_column(String(256))
    reference_key: Mapped[str | None] = mapped_column(String(64))
    caliber_key: Mapped[str | None] = mapped_column(String(128))
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    source: Mapped[str] = mapped_column(String(1))


class ListingSnapshot(Base):
    __tablename__ = "listing_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    raw_item_json: Mapped[dict | None] = mapped_column(JSONB)

    listing = relationship("Listing", back_populates="snapshots")


class ParsedAttribute(Base):
    __tablename__ = "parsed_attributes"
    __table_args__ = (UniqueConstraint("listing_id", "namespace", "key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    namespace: Mapped[str] = mapped_column(String(64), default="watch")
    key: Mapped[str] = mapped_column(String(128))
    value_text: Mapped[str | None] = mapped_column(Text)

    listing = relationship("Listing", back_populates="parsed_attributes")


class RepairSignal(Base):
    __tablename__ = "repair_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    signal_type: Mapped[str] = mapped_column(String(64))
    matched_text: Mapped[str | None] = mapped_column(String(512))
    source_field: Mapped[str | None] = mapped_column(String(64))

    listing = relationship("Listing", back_populates="repair_signals")


class OpportunityScore(Base):
    __tablename__ = "opportunity_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    estimated_resale: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    estimated_repair_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    advised_max_buy: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    potential_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    risk: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    explanations: Mapped[list | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    listing = relationship("Listing", back_populates="opportunity_scores")


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    filter_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_text: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotInterestedListing(Base):
    """Blocklist for eBay item ids a user marked as not interested."""

    __tablename__ = "not_interested_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ebay_item_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    last_listing_title: Mapped[str | None] = mapped_column(Text)
    last_listing_web_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
