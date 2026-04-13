"""Refresh one listing from Buy Browse getItem + eBay page marker active check."""

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
    *,
    browse: EbayBrowseClient | None = None,
) -> Literal["updated", "ended"]:
    """
    GET /item/{id} for this row's ebay_item_id, then verify active state from web page marker.

    - **updated** — item merged (or unavailable from Browse API) and listing does not show ended marker
    - **ended** — eBay page shows "We looked everywhere." marker; ``is_active`` set False

    Pass ``browse`` to reuse one OAuth token across many getItem calls (e.g. stale batch).
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

    browse_client = browse or EbayBrowseClient(
        settings, EbayAuthClient(settings, db)
    )
    now = datetime.now(UTC)

    try:
        raw = browse_client.get_item(listing.ebay_item_id)
    finally:
        increment_browse_get_item(db)
        db.flush()

    if raw is None:
        ended_marker = browse_client.page_has_not_found_marker(
            listing.web_url, item_id=listing.ebay_item_id
        )
        # Robust fallback:
        # - explicit ended marker => inactive
        # - explicit non-ended marker => active
        # - unknown (e.g. repeated 5xx) => keep prior flag unchanged
        if ended_marker is True:
            listing.is_active = False
        elif ended_marker is False:
            listing.is_active = True
        listing.last_seen_at = now
        db.commit()
        if ended_marker is True:
            logger.info(
                "eBay page marker indicates ended listing — marked inactive %s",
                listing.ebay_item_id,
            )
            return "ended"
        logger.info("Browse getItem unavailable and page state unknown; kept prior flag %s", listing.ebay_item_id)
        return "updated"

    fields = browse_item_to_listing_fields(raw)
    for k, v in fields.items():
        if k in ("ebay_item_id", "first_seen_at"):
            continue
        setattr(listing, k, v)
    listing.last_seen_at = now
    ended_marker = browse_client.page_has_not_found_marker(
        fields.get("web_url") or listing.web_url,
        item_id=listing.ebay_item_id,
    )
    ended_at = listing.listing_ended_at
    ended_by_payload = bool(ended_at and ended_at <= now)
    # Multi-signal active check:
    # 1) page ended/sold marker
    # 2) Browse payload itemEndDate in the past
    listing.is_active = not (ended_marker is True or ended_by_payload)
    db.add(
        ListingSnapshot(
            listing_id=listing.id,
            snapshot_at=now,
            raw_item_json=fields["raw_item_json"],
        )
    )
    analyze_listing(db, listing)
    db.commit()
    return "ended" if (ended_marker is True or ended_by_payload) else "updated"
