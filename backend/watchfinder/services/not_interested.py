from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.models import Listing, NotInterestedListing
from watchfinder.services.watch_models import refresh_watch_model_observed_bounds


def mark_listing_not_interested(
    db: Session,
    listing: Listing,
    *,
    source: str = "manual",
    reason: str = "not_interested",
) -> NotInterestedListing:
    stmt = select(NotInterestedListing).where(
        NotInterestedListing.ebay_item_id == listing.ebay_item_id
    )
    row = db.execute(stmt).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        row = NotInterestedListing(
            ebay_item_id=listing.ebay_item_id,
            source=source,
            reason=reason,
            last_listing_title=listing.title,
            last_listing_web_url=listing.web_url,
            is_active=True,
        )
        db.add(row)
    else:
        row.source = source
        row.reason = reason
        row.last_listing_title = listing.title or row.last_listing_title
        row.last_listing_web_url = listing.web_url or row.last_listing_web_url
        row.is_active = True
        row.restored_at = None
        row.updated_at = now
        db.add(row)

    old_watch_model_id = listing.watch_model_id
    db.delete(listing)
    db.flush()
    if old_watch_model_id:
        refresh_watch_model_observed_bounds(db, old_watch_model_id)
    return row


def mark_listing_id_not_interested(
    db: Session,
    listing_id: UUID,
    *,
    source: str = "manual",
    reason: str = "not_interested",
) -> NotInterestedListing:
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return mark_listing_not_interested(db, listing, source=source, reason=reason)


def restore_not_interested_item(db: Session, row_id: UUID) -> NotInterestedListing:
    row = db.get(NotInterestedListing, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not-interested record not found")
    row.is_active = False
    row.restored_at = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    return row
