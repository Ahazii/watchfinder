"""Refresh one listing from Buy Browse getItem — live price/title and is_active."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from watchfinder.config import Settings, get_settings
from watchfinder.models import Listing, ListingSnapshot
from watchfinder.services.ebay import EbayAuthClient, EbayBrowseClient
from watchfinder.services.ebay.api_usage import increment_browse_get_item
from watchfinder.services.ingestion.mapper import browse_item_to_listing_fields
from watchfinder.services.pipeline import analyze_listing

logger = logging.getLogger(__name__)


def refresh_listing_from_ebay(
    db: Session,
    listing_id: UUID,
    settings: Settings | None = None,
) -> Literal["updated", "ended"]:
    """
    GET /item/{id} for this row's ebay_item_id.

    - **updated** — item found; row merged and re-analyzed
    - **ended** — 404; ``is_active`` set False
    """
    settings = settings or get_settings()
    stmt = (
        select(Listing)
        .options(selectinload(Listing.parsed_attributes))
        .where(Listing.id == listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if listing is None:
        raise ValueError("Listing not found")

    auth = EbayAuthClient(settings, db)
    browse = EbayBrowseClient(settings, auth)
    now = datetime.now(UTC)

    try:
        raw = browse.get_item(listing.ebay_item_id)
    finally:
        increment_browse_get_item(db)
        db.flush()

    if raw is None:
        listing.is_active = False
        listing.last_seen_at = now
        db.commit()
        logger.info("eBay getItem 404 — marked inactive %s", listing.ebay_item_id)
        return "ended"

    fields = browse_item_to_listing_fields(raw)
    for k, v in fields.items():
        if k in ("ebay_item_id", "first_seen_at"):
            continue
        setattr(listing, k, v)
    listing.last_seen_at = now
    listing.is_active = True
    db.add(
        ListingSnapshot(
            listing_id=listing.id,
            snapshot_at=now,
            raw_item_json=fields["raw_item_json"],
        )
    )
    analyze_listing(db, listing)
    db.commit()
    return "updated"
