"""Pending rows for manual watch catalog matching."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from watchfinder.models import Listing, ListingEdit, WatchModel, WatchModelLinkReview
from watchfinder.services.valuation.effective import (
    effective_model_family,
    effective_reference,
)
from watchfinder.services.watch_models.candidates import rank_watch_model_candidates
from watchfinder.services.watch_models.match import _find_by_brand_ref


def delete_pending_reviews_for_listing(db: Session, listing_id) -> None:
    db.execute(
        delete(WatchModelLinkReview).where(
            WatchModelLinkReview.listing_id == listing_id,
            WatchModelLinkReview.status == "pending",
        )
    )


def upsert_pending_watch_link_review(
    db: Session,
    listing: Listing,
    parsed: dict[str, str],
    edit: ListingEdit | None,
    candidates: list[tuple[WatchModel, float]],
) -> WatchModelLinkReview:
    brand = (parsed.get("brand") or "").strip() or ""
    ref, _ = effective_reference(parsed, edit)
    mf, _ = effective_model_family(parsed, edit)
    mf_clean = (mf or "").strip()

    best = float(candidates[0][1]) if candidates else 0.0
    if best >= 0.85:
        tier = "high"
    elif best >= 0.5:
        tier = "medium"
    else:
        tier = "low"

    reasons: list[str] = []
    if ref and brand and _find_by_brand_ref(db, brand, ref) is None:
        reasons.append("no_exact_reference_row")
    if not candidates:
        reasons.append("no_similar_catalog_rows")
    elif best < 0.85:
        reasons.append("uncertain_best_match")

    ids = [str(w.id) for w, _ in candidates]
    scores = {str(w.id): round(float(s), 4) for w, s in candidates}

    stmt = select(WatchModelLinkReview).where(
        WatchModelLinkReview.listing_id == listing.id,
        WatchModelLinkReview.status == "pending",
    )
    row = db.execute(stmt).scalar_one_or_none()
    conf = Decimal(str(round(best, 4)))
    if row:
        row.confidence = conf
        row.tier = tier
        row.reason_codes = reasons
        row.candidate_watch_model_ids = ids
        row.candidate_scores = scores
        row.updated_at = datetime.now(timezone.utc)
        db.add(row)
        return row
    rev = WatchModelLinkReview(
        listing_id=listing.id,
        status="pending",
        confidence=conf,
        tier=tier,
        reason_codes=reasons,
        candidate_watch_model_ids=ids,
        candidate_scores=scores,
    )
    db.add(rev)
    db.flush()
    return rev
