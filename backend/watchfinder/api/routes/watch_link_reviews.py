from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from watchfinder.api.deps import get_db
from watchfinder.models import Listing, ListingEdit, WatchModel, WatchModelLinkReview
from watchfinder.schemas.watch_link_reviews import (
    ResolveWatchLinkReviewBody,
    ResolveWatchLinkReviewResponse,
    WatchLinkReviewDetailOut,
    WatchLinkReviewListItem,
    WatchLinkReviewListResponse,
)
from watchfinder.schemas.watch_models import BackfillWatchCatalogResponse, WatchModelOut
from watchfinder.services.watch_models import refresh_watch_model_observed_bounds
from watchfinder.services.watch_models.catalog import (
    CatalogLinkOutcome,
    create_catalog_from_listing_identity,
    sync_unmatched_listings_watch_catalog,
)
from watchfinder.services.not_interested import mark_listing_id_not_interested

router = APIRouter(prefix="/watch-link-reviews", tags=["watch-link-reviews"])


@router.post(
    "/sync-from-unmatched",
    response_model=BackfillWatchCatalogResponse,
    summary="Re-analyze listings without a catalog link (match queue / auto-link)",
)
def sync_unmatched_to_match_queue(db: Session = Depends(get_db)) -> BackfillWatchCatalogResponse:
    stats = sync_unmatched_listings_watch_catalog(db)
    db.commit()
    return BackfillWatchCatalogResponse(**stats)


def _candidate_models(
    db: Session, review: WatchModelLinkReview
) -> tuple[list[WatchModelOut], dict[str, float]]:
    ids = review.candidate_watch_model_ids or []
    raw_scores = review.candidate_scores or {}
    out: list[WatchModelOut] = []
    for sid in ids:
        try:
            uid = UUID(str(sid))
        except ValueError:
            continue
        wm = db.get(WatchModel, uid)
        if wm:
            out.append(WatchModelOut.model_validate(wm))
    scores = {str(k): float(v) for k, v in raw_scores.items()}
    return out, scores


@router.get("", response_model=WatchLinkReviewListResponse)
def list_pending_watch_link_reviews(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> WatchLinkReviewListResponse:
    base = (
        select(WatchModelLinkReview, Listing)
        .join(Listing, WatchModelLinkReview.listing_id == Listing.id)
        .where(WatchModelLinkReview.status == "pending")
    )
    total = int(
        db.scalar(
            select(func.count())
            .select_from(WatchModelLinkReview)
            .where(WatchModelLinkReview.status == "pending")
        )
        or 0
    )
    rows = db.execute(
        base.order_by(WatchModelLinkReview.created_at.asc()).offset(skip).limit(limit)
    ).all()
    items: list[WatchLinkReviewListItem] = []
    for rev, lst in rows:
        cids = rev.candidate_watch_model_ids or []
        items.append(
            WatchLinkReviewListItem(
                id=rev.id,
                listing_id=rev.listing_id,
                ebay_item_id=lst.ebay_item_id,
                listing_title=lst.title,
                tier=rev.tier,
                confidence=rev.confidence,
                candidate_count=len(cids),
                reason_codes=list(rev.reason_codes) if rev.reason_codes else None,
                created_at=rev.created_at,
            )
        )
    return WatchLinkReviewListResponse(items=items, total=total)


@router.get("/{review_id}", response_model=WatchLinkReviewDetailOut)
def get_watch_link_review(review_id: UUID, db: Session = Depends(get_db)) -> WatchLinkReviewDetailOut:
    rev = db.get(WatchModelLinkReview, review_id)
    if not rev or rev.status != "pending":
        raise HTTPException(status_code=404, detail="Review not found or already resolved")
    lst = db.get(Listing, rev.listing_id)
    if not lst:
        raise HTTPException(status_code=404, detail="Listing missing")
    models, scores = _candidate_models(db, rev)
    return WatchLinkReviewDetailOut(
        id=rev.id,
        listing_id=rev.listing_id,
        ebay_item_id=lst.ebay_item_id,
        listing_title=lst.title,
        listing_web_url=lst.web_url,
        tier=rev.tier,
        confidence=rev.confidence,
        reason_codes=list(rev.reason_codes) if rev.reason_codes else None,
        candidate_watch_models=models,
        candidate_scores=scores,
        created_at=rev.created_at,
    )


@router.post("/{review_id}/resolve", response_model=ResolveWatchLinkReviewResponse)
def resolve_watch_link_review(
    review_id: UUID,
    body: ResolveWatchLinkReviewBody,
    db: Session = Depends(get_db),
) -> ResolveWatchLinkReviewResponse:
    action = (body.action or "").strip().lower()
    if action not in ("match", "create", "dismiss"):
        raise HTTPException(status_code=400, detail="action must be match, create, or dismiss")

    rev = db.get(WatchModelLinkReview, review_id)
    if not rev or rev.status != "pending":
        raise HTTPException(status_code=404, detail="Review not found or already resolved")

    stmt = (
        select(Listing)
        .options(selectinload(Listing.parsed_attributes))
        .where(Listing.id == rev.listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    now = datetime.now(timezone.utc)

    if action == "dismiss":
        rev.status = "dismissed"
        rev.resolved_at = now
        db.commit()
        return ResolveWatchLinkReviewResponse(
            status="dismissed",
            listing_id=listing.id,
            watch_model_id=listing.watch_model_id,
        )

    if action == "match":
        if body.watch_model_id is None:
            raise HTTPException(
                status_code=400,
                detail="watch_model_id required for match",
            )
        wm = db.get(WatchModel, body.watch_model_id)
        if not wm:
            raise HTTPException(status_code=404, detail="Watch model not found")
        listing.watch_model_id = wm.id
        rev.status = "resolved_match"
        rev.resolved_at = now
        refresh_watch_model_observed_bounds(db, wm.id)
        db.commit()
        return ResolveWatchLinkReviewResponse(
            status="resolved_match",
            listing_id=listing.id,
            watch_model_id=listing.watch_model_id,
        )

    parsed = {a.key: (a.value_text or "") for a in listing.parsed_attributes}
    edit = db.get(ListingEdit, listing.id)
    out = create_catalog_from_listing_identity(db, listing, parsed, edit)
    if out == CatalogLinkOutcome.SKIPPED_NO_IDENTITY:
        raise HTTPException(
            status_code=400,
            detail="Cannot create catalog row: add brand plus reference or model family on the listing.",
        )
    if out == CatalogLinkOutcome.SKIPPED_EXCLUDED_BRAND:
        raise HTTPException(
            status_code=400,
            detail="This brand is listed in WATCH_CATALOG_EXCLUDED_BRANDS (server env).",
        )
    rev.status = "resolved_create"
    rev.resolved_at = now
    if listing.watch_model_id:
        refresh_watch_model_observed_bounds(db, listing.watch_model_id)
    db.commit()
    return ResolveWatchLinkReviewResponse(
        status="resolved_create",
        listing_id=listing.id,
        watch_model_id=listing.watch_model_id,
    )


@router.post("/{review_id}/not-interested", response_model=dict)
def mark_review_listing_not_interested(
    review_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    rev = db.get(WatchModelLinkReview, review_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Review not found")
    row = mark_listing_id_not_interested(
        db,
        rev.listing_id,
        source="match_queue",
        reason="user_not_interested",
    )
    db.commit()
    return {"status": "ok", "not_interested_id": str(row.id), "ebay_item_id": row.ebay_item_id}
