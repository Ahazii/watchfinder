from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from watchfinder.api.deps import get_db
from watchfinder.api.listing_detail import build_listing_detail
from watchfinder.api.listing_helpers import listing_to_summary, scores_for_listings
from watchfinder.api.query import base_listing_select, count_listings
from watchfinder.models import Listing, ListingEdit
from watchfinder.schemas.listings import (
    ListingDetail,
    ListingEditsPatch,
    ListingListResponse,
    OpportunityScoreOut,
    ParsedAttributeOut,
    RepairSignalOut,
)
from watchfinder.services.pipeline import analyze_listing
from watchfinder.services.valuation.sales_sync import sync_watch_sale_record
from watchfinder.services.watch_models import refresh_watch_model_observed_bounds

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


def _listing_detail_options():
    return (
        selectinload(Listing.parsed_attributes),
        selectinload(Listing.repair_signals),
        selectinload(Listing.opportunity_scores),
        selectinload(Listing.listing_edit),
        selectinload(Listing.watch_model),
    )


@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing(listing_id: UUID, db: Session = Depends(get_db)) -> ListingDetail:
    stmt = (
        select(Listing)
        .options(*_listing_detail_options())
        .where(Listing.id == listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return build_listing_detail(db, listing)


@router.patch("/{listing_id}", response_model=ListingDetail)
def patch_listing(
    listing_id: UUID, body: ListingEditsPatch, db: Session = Depends(get_db)
) -> ListingDetail:
    stmt = (
        select(Listing)
        .options(*_listing_detail_options())
        .where(Listing.id == listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    edit = listing.listing_edit
    if edit is None:
        edit = ListingEdit(listing_id=listing.id)
        db.add(edit)
        listing.listing_edit = edit

    old_watch_model_id = listing.watch_model_id
    patch = body.model_dump(exclude_unset=True)
    if "watch_model_id" in patch:
        listing.watch_model_id = patch.pop("watch_model_id")

    for key, val in patch.items():
        if hasattr(edit, key):
            setattr(edit, key, val)

    db.flush()
    parsed = {a.key: (a.value_text or "") for a in listing.parsed_attributes}
    sync_watch_sale_record(db, listing, parsed, edit)
    analyze_listing(db, listing)
    if old_watch_model_id and old_watch_model_id != listing.watch_model_id:
        refresh_watch_model_observed_bounds(db, old_watch_model_id)
    db.commit()

    listing = db.execute(
        select(Listing).options(*_listing_detail_options()).where(Listing.id == listing_id)
    ).scalar_one()
    return build_listing_detail(db, listing)
