from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.api.listing_helpers import listing_to_summary, scores_for_listings
from watchfinder.api.listing_sort import apply_listing_sort, normalize_sort
from watchfinder.api.query import base_listing_select, count_listings
from watchfinder.schemas.listings import ListingListResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=ListingListResponse)
def list_candidates(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    title_q: str | None = Query(
        None,
        description="Case-insensitive substring match on listing title only",
    ),
    text_q: str | None = Query(
        None,
        description="Case-insensitive substring across title, URLs, condition, JSON, parsed attributes, repair signals",
    ),
    brand: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    repair_keyword: str | None = None,
    condition_q: str | None = None,
    movement: str | None = None,
    caliber_known: bool | None = None,
    confidence_min: Decimal | None = None,
    profit_min: Decimal | None = None,
    sale_type: str | None = Query(
        None,
        description="Filter sale format, e.g. AUCTION, FIXED_PRICE, BEST_OFFER",
    ),
    ending_within_hours: int | None = Query(
        None,
        ge=0,
        le=720,
        description="Only listings ending within N hours from now",
    ),
    listing_active: Literal["active", "inactive", "all"] = Query(
        "active",
        description="Filter by row flag: active listings, inactive only, or all",
    ),
    exclude_quartz: bool = Query(
        False,
        description="Omit rows whose title or parsed movement mentions quartz",
    ),
    resolved_brand_id: UUID | None = Query(
        None,
        description="Filter by resolved dictionary brand id",
    ),
    resolved_stock_reference_id: UUID | None = Query(
        None,
        description="Filter by resolved stock reference id",
    ),
    caliber_id: UUID | None = Query(
        None,
        description="Filter listings linked to this caliber row",
    ),
    sort_by: str | None = Query(
        None,
        description="Sort column: last_seen, title, price, confidence, profit",
    ),
    sort_dir: str | None = Query(None, description="asc or desc"),
) -> ListingListResponse:
    """Repair/resale candidates: opportunity score with potential_profit > 0."""
    base = base_listing_select(
        listing_active=listing_active,
        title_q=title_q,
        text_q=text_q,
        brand=brand,
        price_min=price_min,
        price_max=price_max,
        repair_keyword=repair_keyword,
        condition_q=condition_q,
        movement=movement,
        caliber_known=caliber_known,
        confidence_min=confidence_min,
        profit_min=profit_min,
        sale_type=sale_type,
        ending_within_hours=ending_within_hours,
        candidates_only=True,
        exclude_quartz=exclude_quartz,
        resolved_brand_id=resolved_brand_id,
        resolved_stock_reference_id=resolved_stock_reference_id,
        caliber_id=caliber_id,
    )
    total = count_listings(db, base)
    sk, desc = normalize_sort(sort_by, sort_dir)
    stmt = apply_listing_sort(base, sort_by=sk, descending=desc).offset(skip).limit(limit)
    rows = db.execute(stmt).scalars().all()
    score_map = scores_for_listings(db, [r.id for r in rows])
    items = [listing_to_summary(r, score_map.get(r.id)) for r in rows]
    return ListingListResponse(items=items, total=total, skip=skip, limit=limit)
