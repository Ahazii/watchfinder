"""Composable filters for listing queries (no duplicate rows from joins)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, Text, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from watchfinder.models import (
    Listing,
    ListingCaliber,
    OpportunityScore,
    ParsedAttribute,
    RepairSignal,
)
from watchfinder.services.listing_status import active_listing_clause, inactive_listing_clause


def base_listing_select(
    *,
    listing_active: str = "active",
    title_q: str | None = None,
    text_q: str | None = None,
    brand: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    repair_keyword: str | None = None,
    condition_q: str | None = None,
    movement: str | None = None,
    caliber_known: bool | None = None,
    confidence_min: Decimal | None = None,
    profit_min: Decimal | None = None,
    sale_type: str | None = None,
    ending_within_hours: int | None = None,
    candidates_only: bool = False,
    exclude_quartz: bool = False,
    resolved_brand_id: uuid.UUID | None = None,
    resolved_stock_reference_id: uuid.UUID | None = None,
    caliber_id: uuid.UUID | None = None,
    listing_type: str | None = None,
) -> Select:
    stmt: Select = select(Listing)

    la = (listing_active or "active").strip().lower()
    if la == "active":
        stmt = stmt.where(active_listing_clause())
    elif la == "inactive":
        stmt = stmt.where(inactive_listing_clause())
    # "all" — no is_active filter

    if title_q:
        t = f"%{title_q.strip()}%"
        stmt = stmt.where(Listing.title.ilike(t))

    if text_q and text_q.strip():
        raw = text_q.strip()
        t = f"%{raw}%"
        stmt = stmt.where(
            or_(
                Listing.title.ilike(t),
                Listing.subtitle.ilike(t),
                Listing.web_url.ilike(t),
                Listing.ebay_item_id.ilike(t),
                Listing.condition_description.ilike(t),
                Listing.category_path.ilike(t),
                Listing.seller_username.ilike(t),
                cast(Listing.buying_options, Text).ilike(t),
                cast(Listing.item_aspects, Text).ilike(t),
                cast(Listing.raw_item_json, Text).ilike(t),
                exists(
                    select(1).where(
                        ParsedAttribute.listing_id == Listing.id,
                        ParsedAttribute.value_text.ilike(t),
                    )
                ),
                exists(
                    select(1).where(
                        RepairSignal.listing_id == Listing.id,
                        RepairSignal.matched_text.ilike(t),
                    )
                ),
            )
        )

    if brand:
        b = f"%{brand.strip()}%"
        stmt = stmt.where(
            or_(
                Listing.title.ilike(b),
                exists(
                    select(1).where(
                        ParsedAttribute.listing_id == Listing.id,
                        ParsedAttribute.namespace == "watch",
                        ParsedAttribute.key == "brand",
                        ParsedAttribute.value_text.ilike(b),
                    )
                ),
            )
        )

    if resolved_brand_id is not None:
        stmt = stmt.where(Listing.resolved_brand_id == resolved_brand_id)
    if resolved_stock_reference_id is not None:
        stmt = stmt.where(
            Listing.resolved_stock_reference_id == resolved_stock_reference_id
        )
    if caliber_id is not None:
        stmt = stmt.where(
            exists(
                select(1).where(
                    ListingCaliber.listing_id == Listing.id,
                    ListingCaliber.caliber_id == caliber_id,
                )
            )
        )
    if listing_type and str(listing_type).strip():
        stmt = stmt.where(Listing.listing_type == str(listing_type).strip())

    if price_min is not None:
        stmt = stmt.where(Listing.current_price.is_not(None)).where(
            Listing.current_price >= price_min
        )
    if price_max is not None:
        stmt = stmt.where(Listing.current_price.is_not(None)).where(
            Listing.current_price <= price_max
        )

    if repair_keyword:
        kw = f"%{repair_keyword.strip()}%"
        stmt = stmt.where(
            exists(
                select(1).where(
                    RepairSignal.listing_id == Listing.id,
                    or_(
                        RepairSignal.matched_text.ilike(kw),
                        RepairSignal.signal_type.ilike(kw),
                    ),
                )
            )
        )

    if condition_q:
        cq = f"%{condition_q.strip()}%"
        stmt = stmt.where(
            or_(
                Listing.condition_description.ilike(cq),
                Listing.condition_id.ilike(cq),
            )
        )

    if movement:
        mv = f"%{movement.strip()}%"
        stmt = stmt.where(
            exists(
                select(1).where(
                    ParsedAttribute.listing_id == Listing.id,
                    ParsedAttribute.namespace == "watch",
                    ParsedAttribute.key == "movement",
                    ParsedAttribute.value_text.ilike(mv),
                )
            )
        )

    if caliber_known is True:
        stmt = stmt.where(
            exists(
                select(1).where(
                    ParsedAttribute.listing_id == Listing.id,
                    ParsedAttribute.namespace == "watch",
                    ParsedAttribute.key == "caliber",
                    ParsedAttribute.value_text.is_not(None),
                )
            )
        )
    elif caliber_known is False:
        stmt = stmt.where(
            ~exists(
                select(1).where(
                    ParsedAttribute.listing_id == Listing.id,
                    ParsedAttribute.namespace == "watch",
                    ParsedAttribute.key == "caliber",
                    ParsedAttribute.value_text.is_not(None),
                )
            )
        )

    if confidence_min is not None:
        stmt = stmt.where(
            exists(
                select(1).where(
                    OpportunityScore.listing_id == Listing.id,
                    OpportunityScore.confidence >= confidence_min,
                )
            )
        )

    if profit_min is not None:
        stmt = stmt.where(
            exists(
                select(1).where(
                    OpportunityScore.listing_id == Listing.id,
                    OpportunityScore.potential_profit >= profit_min,
                )
            )
        )

    if sale_type and sale_type.strip():
        st = f"%{sale_type.strip().lower()}%"
        stmt = stmt.where(func.lower(cast(Listing.buying_options, Text)).ilike(st))

    if ending_within_hours is not None:
        now = datetime.now(UTC)
        horizon = now + timedelta(hours=max(0, int(ending_within_hours)))
        stmt = stmt.where(
            Listing.listing_ended_at.is_not(None),
            Listing.listing_ended_at > now,
            Listing.listing_ended_at <= horizon,
        )

    if candidates_only:
        stmt = stmt.where(
            exists(
                select(1).where(
                    OpportunityScore.listing_id == Listing.id,
                    OpportunityScore.potential_profit > 0,
                )
            )
        )

    if exclude_quartz:
        qz = "%quartz%"
        stmt = stmt.where(~Listing.title.ilike(qz)).where(
            ~exists(
                select(1).where(
                    ParsedAttribute.listing_id == Listing.id,
                    ParsedAttribute.namespace == "watch",
                    ParsedAttribute.key == "movement",
                    ParsedAttribute.value_text.ilike(qz),
                )
            )
        )

    return stmt


def count_listings(db: Session, stmt: Select) -> int:
    subq = stmt.subquery()
    c_stmt = select(func.count()).select_from(subq)
    n = db.scalar(c_stmt)
    return int(n or 0)
