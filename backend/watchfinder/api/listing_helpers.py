from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.models import Listing, OpportunityScore
from watchfinder.schemas.listings import ListingSummary, OpportunityScoreOut


def scores_for_listings(db: Session, listing_ids: list[UUID]) -> dict[UUID, OpportunityScore]:
    if not listing_ids:
        return {}
    rows = db.execute(
        select(OpportunityScore).where(OpportunityScore.listing_id.in_(listing_ids))
    ).scalars().all()
    return {r.listing_id: r for r in rows}


def listing_to_summary(
    listing: Listing, score: OpportunityScore | None
) -> ListingSummary:
    return ListingSummary(
        id=listing.id,
        ebay_item_id=listing.ebay_item_id,
        title=listing.title,
        current_price=listing.current_price,
        currency=listing.currency,
        web_url=listing.web_url,
        condition_description=listing.condition_description,
        buying_options=list(listing.buying_options) if isinstance(listing.buying_options, list) else None,
        listing_ended_at=listing.listing_ended_at,
        last_seen_at=listing.last_seen_at,
        first_seen_at=listing.first_seen_at,
        is_active=listing.is_active,
        image_urls=listing.image_urls,
        watch_model_id=listing.watch_model_id,
        resolved_brand_id=listing.resolved_brand_id,
        resolved_stock_reference_id=listing.resolved_stock_reference_id,
        listing_type=listing.listing_type or "unknown",
        listing_type_source=listing.listing_type_source or "auto",
        score=OpportunityScoreOut.model_validate(score) if score else None,
    )
