from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from watchfinder.db import Base


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    display_name: Mapped[str] = mapped_column(String(512), index=True)
    norm_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    stock_references = relationship(
        "StockReference", back_populates="brand", passive_deletes=True
    )
    caliber_links = relationship(
        "CaliberBrandLink", back_populates="brand", passive_deletes=True
    )


class Caliber(Base):
    __tablename__ = "calibers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    display_text: Mapped[str] = mapped_column(Text)
    norm_key: Mapped[str] = mapped_column(Text, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    brand_links = relationship(
        "CaliberBrandLink", back_populates="caliber", passive_deletes=True
    )
    stock_reference_links = relationship(
        "CaliberStockReferenceLink", back_populates="caliber", passive_deletes=True
    )
    listing_links = relationship(
        "ListingCaliber", back_populates="caliber", passive_deletes=True
    )


class StockReference(Base):
    __tablename__ = "stock_references"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    ref_text: Mapped[str] = mapped_column(Text)
    norm_key: Mapped[str] = mapped_column(Text)
    watch_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watch_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("brand_id", "norm_key", name="uq_stock_references_brand_norm"),)

    brand = relationship("Brand", back_populates="stock_references")
    watch_model = relationship("WatchModel", back_populates="stock_references")
    caliber_links = relationship(
        "CaliberStockReferenceLink", back_populates="stock_reference", passive_deletes=True
    )


class CaliberBrandLink(Base):
    __tablename__ = "caliber_brand_links"

    caliber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calibers.id", ondelete="CASCADE"), primary_key=True
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), primary_key=True
    )

    caliber = relationship("Caliber", back_populates="brand_links")
    brand = relationship("Brand", back_populates="caliber_links")


class CaliberStockReferenceLink(Base):
    __tablename__ = "caliber_stock_reference_links"

    caliber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calibers.id", ondelete="CASCADE"), primary_key=True
    )
    stock_reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_references.id", ondelete="CASCADE"),
        primary_key=True,
    )

    caliber = relationship("Caliber", back_populates="stock_reference_links")
    stock_reference = relationship("StockReference", back_populates="caliber_links")


class ListingCaliber(Base):
    __tablename__ = "listing_calibers"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True
    )
    caliber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calibers.id", ondelete="CASCADE"), primary_key=True
    )

    listing = relationship("Listing", back_populates="listing_calibers")
    caliber = relationship("Caliber", back_populates="listing_links")
