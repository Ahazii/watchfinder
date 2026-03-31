from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.api.listing_helpers import listing_to_summary, scores_for_listings
from watchfinder.api.query import base_listing_select, count_listings
from watchfinder.models import Listing
from watchfinder.schemas.listings import ListingListResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=ListingListResponse)
def list_candidates(
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
    """Repair/resale candidates: opportunity score with potential_profit > 0."""
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
        candidates_only=True,
    )
    total = count_listings(db, base)
    stmt = base.order_by(Listing.last_seen_at.desc()).offset(skip).limit(limit)
    rows = db.execute(stmt).scalars().all()
    score_map = scores_for_listings(db, [r.id for r in rows])
    items = [listing_to_summary(r, score_map.get(r.id)) for r in rows]
    return ListingListResponse(items=items, total=total, skip=skip, limit=limit)
