from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from watchfinder.api.deps import get_db
from watchfinder.api.listing_helpers import listing_to_summary, scores_for_listings
from watchfinder.api.query import base_listing_select, count_listings
from watchfinder.models import Listing
from watchfinder.schemas.listings import (
    ListingDetail,
    ListingListResponse,
    OpportunityScoreOut,
    ParsedAttributeOut,
    RepairSignalOut,
)

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=ListingListResponse)
def list_listings(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    brand: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    repair_keyword: str | None = None,
    condition_q: str | None = None,
    movement: str | None = None,
    caliber_known: bool | None = None,
    confidence_min: Decimal | None = None,
    profit_min: Decimal | None = None,
) -> ListingListResponse:
    base = base_listing_select(
        active_only=True,
        brand=brand,
        price_min=price_min,
        price_max=price_max,
        repair_keyword=repair_keyword,
        condition_q=condition_q,
        movement=movement,
        caliber_known=caliber_known,
        confidence_min=confidence_min,
        profit_min=profit_min,
        candidates_only=False,
    )
    total = count_listings(db, base)
    stmt = (
        base.order_by(Listing.last_seen_at.desc()).offset(skip).limit(limit)
    )
    rows = db.execute(stmt).scalars().all()
    score_map = scores_for_listings(db, [r.id for r in rows])
    items = [listing_to_summary(r, score_map.get(r.id)) for r in rows]
    return ListingListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing(listing_id: UUID, db: Session = Depends(get_db)) -> ListingDetail:
    stmt = (
        select(Listing)
        .options(
            selectinload(Listing.parsed_attributes),
            selectinload(Listing.repair_signals),
            selectinload(Listing.opportunity_scores),
        )
        .where(Listing.id == listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    scores = sorted(
        listing.opportunity_scores,
        key=lambda s: s.computed_at.timestamp()
        if s.computed_at
        else 0.0,
        reverse=True,
    )
    latest = scores[0] if scores else None

    return ListingDetail(
        id=listing.id,
        ebay_item_id=listing.ebay_item_id,
        title=listing.title,
        subtitle=listing.subtitle,
        current_price=listing.current_price,
        currency=listing.currency,
        web_url=listing.web_url,
        condition_description=listing.condition_description,
        last_seen_at=listing.last_seen_at,
        first_seen_at=listing.first_seen_at,
        is_active=listing.is_active,
        image_urls=listing.image_urls,
        shipping_price=listing.shipping_price,
        seller_username=listing.seller_username,
        category_path=listing.category_path,
        score=OpportunityScoreOut.model_validate(latest) if latest else None,
        parsed_attributes=[
            ParsedAttributeOut.model_validate(x) for x in listing.parsed_attributes
        ],
        repair_signals=[
            RepairSignalOut.model_validate(x) for x in listing.repair_signals
        ],
        opportunity_scores=[OpportunityScoreOut.model_validate(s) for s in scores],
    )
