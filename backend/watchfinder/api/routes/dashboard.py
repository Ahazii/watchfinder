from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.api.listing_helpers import listing_to_summary, scores_for_listings
from watchfinder.models import Listing, OpportunityScore, RepairSignal
from watchfinder.schemas.listings import DashboardStats
from watchfinder.services.ebay.api_usage import get_ebay_api_usage

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db)) -> DashboardStats:
    total_listings = int(
        db.scalar(select(func.count()).select_from(Listing)) or 0
    )
    active_listings = int(
        db.scalar(
            select(func.count()).select_from(Listing).where(Listing.is_active.is_(True))
        )
        or 0
    )
    candidate_count = int(
        db.scalar(
            select(func.count())
            .select_from(OpportunityScore)
            .where(OpportunityScore.potential_profit > 0)
        )
        or 0
    )
    distinct_signals = select(RepairSignal.listing_id).distinct().subquery()
    listings_with_repair_signals = int(
        db.scalar(select(func.count()).select_from(distinct_signals)) or 0
    )

    recent = db.execute(
        select(Listing)
        .where(Listing.is_active.is_(True))
        .order_by(Listing.last_seen_at.desc())
        .limit(5)
    ).scalars().all()
    score_map = scores_for_listings(db, [r.id for r in recent])
    recent_summaries = [listing_to_summary(r, score_map.get(r.id)) for r in recent]

    usage = get_ebay_api_usage(db)
    return DashboardStats(
        total_listings=total_listings,
        active_listings=active_listings,
        candidate_count=candidate_count,
        listings_with_repair_signals=listings_with_repair_signals,
        recent_listings=recent_summaries,
        ebay_browse_search_calls=int(usage.get("browse_search", 0)),
        ebay_oauth_token_calls=int(usage.get("oauth_token", 0)),
    )
