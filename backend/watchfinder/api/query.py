"""Composable filters for listing queries (no duplicate rows from joins)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from watchfinder.models import Listing, OpportunityScore, ParsedAttribute, RepairSignal


def base_listing_select(
    *,
    listing_active: str = "active",
    title_q: str | None = None,
    brand: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    repair_keyword: str | None = None,
    condition_q: str | None = None,
    movement: str | None = None,
    caliber_known: bool | None = None,
    confidence_min: Decimal | None = None,
    profit_min: Decimal | None = None,
    candidates_only: bool = False,
    exclude_quartz: bool = False,
) -> Select:
    stmt: Select = select(Listing)

    la = (listing_active or "active").strip().lower()
    if la == "active":
        stmt = stmt.where(Listing.is_active.is_(True))
    elif la == "inactive":
        stmt = stmt.where(Listing.is_active.is_(False))
    # "all" — no is_active filter

    if title_q:
        t = f"%{title_q.strip()}%"
        stmt = stmt.where(Listing.title.ilike(t))

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
