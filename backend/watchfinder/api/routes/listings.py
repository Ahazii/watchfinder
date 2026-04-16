from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from watchfinder.api.deps import get_db
from watchfinder.api.listing_detail import build_listing_detail
from watchfinder.api.listing_helpers import listing_to_summary, scores_for_listings
from watchfinder.api.listing_sort import apply_listing_sort, normalize_sort
from watchfinder.api.query import base_listing_select, count_listings
from watchfinder.models import Listing, ListingEdit, WatchModel
from watchfinder.schemas.listings import (
    ListingType,
    ListingDetail,
    ListingEditsPatch,
    ListingListResponse,
    OpportunityScoreOut,
    ParsedAttributeOut,
    RepairSignalOut,
)
from watchfinder.schemas.watch_models import PromoteWatchCatalogResponse, WatchModelOut
from watchfinder.services.pipeline import analyze_listing
from watchfinder.services.valuation.sales_sync import sync_watch_sale_record
from watchfinder.services.ingestion.live_refresh import refresh_listing_from_ebay
from watchfinder.services.not_interested import mark_listing_id_not_interested
from watchfinder.services.watch_models import (
    CatalogLinkOutcome,
    ensure_watch_catalog_for_listing,
    refresh_watch_model_observed_bounds,
)

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=ListingListResponse)
def list_listings(
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
    listing_type: ListingType | None = Query(
        None,
        description="Filter by listing type classification",
    ),
    sort_by: str | None = Query(
        None,
        description="Sort column: last_seen, title, price, confidence, profit",
    ),
    sort_dir: str | None = Query(None, description="asc or desc"),
) -> ListingListResponse:
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
        candidates_only=False,
        exclude_quartz=exclude_quartz,
        resolved_brand_id=resolved_brand_id,
        resolved_stock_reference_id=resolved_stock_reference_id,
        caliber_id=caliber_id,
        listing_type=listing_type,
    )
    total = count_listings(db, base)
    sk, desc = normalize_sort(sort_by, sort_dir)
    stmt = apply_listing_sort(base, sort_by=sk, descending=desc).offset(skip).limit(limit)
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


@router.post(
    "/{listing_id}/promote-watch-catalog",
    response_model=PromoteWatchCatalogResponse,
    summary="Create or link a watch_models row from this listing",
)
def promote_listing_to_watch_catalog(
    listing_id: UUID, db: Session = Depends(get_db)
) -> PromoteWatchCatalogResponse:
    stmt = (
        select(Listing)
        .options(selectinload(Listing.parsed_attributes))
        .where(Listing.id == listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    parsed = {a.key: (a.value_text or "") for a in listing.parsed_attributes}
    edit = db.get(ListingEdit, listing.id)
    out = ensure_watch_catalog_for_listing(
        db, listing, parsed, edit, bypass_review=True
    )

    if out == CatalogLinkOutcome.SKIPPED_NO_IDENTITY:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot add to watch database: need a parsed brand plus a reference "
                "or model family (edit this listing and save, or fix the title/parsing)."
            ),
        )
    if out == CatalogLinkOutcome.SKIPPED_EXCLUDED_BRAND:
        raise HTTPException(
            status_code=400,
            detail="This brand is listed in WATCH_CATALOG_EXCLUDED_BRANDS (server env).",
        )

    if listing.watch_model_id:
        refresh_watch_model_observed_bounds(db, listing.watch_model_id)
    db.commit()

    wm = db.get(WatchModel, listing.watch_model_id)
    return PromoteWatchCatalogResponse(
        outcome=out.value,
        watch_model=WatchModelOut.model_validate(wm) if wm else None,
    )


@router.post("/{listing_id}/refresh-from-ebay", response_model=ListingDetail)
def post_refresh_listing_from_ebay(
    listing_id: UUID, db: Session = Depends(get_db)
) -> ListingDetail:
    """Live Browse **getItem** for this row: refresh fields, re-analyze, or mark ``is_active=false`` on 404."""
    try:
        refresh_listing_from_ebay(db, listing_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    stmt = (
        select(Listing)
        .options(*_listing_detail_options())
        .where(Listing.id == listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return build_listing_detail(db, listing)


@router.post("/{listing_id}/not-interested", response_model=dict)
def post_mark_not_interested(listing_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Mark listing as not interested: block this eBay id and remove listing row."""
    row = mark_listing_id_not_interested(
        db,
        listing_id,
        source="listings",
        reason="user_not_interested",
    )
    db.commit()
    return {"status": "ok", "not_interested_id": str(row.id), "ebay_item_id": row.ebay_item_id}


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

    lt = patch.pop("listing_type", None)
    lts = patch.pop("listing_type_source", None)
    if lt is not None:
        listing.listing_type = str(lt)
        listing.listing_type_source = "manual"
    elif lts == "auto":
        listing.listing_type_source = "auto"

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
