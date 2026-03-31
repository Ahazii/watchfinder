"""Scheduled ingestion: Browse search → upsert listings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import Listing, ListingSnapshot
from watchfinder.services.ebay import EbayAuthClient, EbayBrowseClient
from watchfinder.services.ingestion.mapper import item_summary_to_listing_fields
from watchfinder.services.pipeline import analyze_listing

logger = logging.getLogger(__name__)


def run_browse_ingest(db: Session, settings: Settings | None = None) -> int:
    """
    Run one Browse search page and upsert listings.
    Returns number of item summaries processed.
    """
    settings = settings or get_settings()
    auth = EbayAuthClient(settings)
    browse = EbayBrowseClient(settings, auth)

    data = browse.search(
        settings.ebay_search_query,
        limit=settings.ebay_search_limit,
        offset=0,
    )
    summaries = data.get("itemSummaries") or []
    now = datetime.now(UTC)
    count = 0

    for raw in summaries:
        if not isinstance(raw, dict):
            continue
        try:
            fields = item_summary_to_listing_fields(raw)
        except ValueError as e:
            logger.warning("Skip summary: %s", e)
            continue

        ebay_id = fields["ebay_item_id"]
        existing = db.execute(
            select(Listing).where(Listing.ebay_item_id == ebay_id)
        ).scalar_one_or_none()

        if existing:
            for k, v in fields.items():
                if k in ("ebay_item_id", "first_seen_at"):
                    continue
                setattr(existing, k, v)
            existing.last_seen_at = now
            existing.is_active = True
            db.add(
                ListingSnapshot(
                    listing_id=existing.id,
                    snapshot_at=now,
                    raw_item_json=fields["raw_item_json"],
                )
            )
            target = existing
        else:
            listing = Listing(**fields, first_seen_at=now, last_seen_at=now)
            db.add(listing)
            db.flush()
            db.add(
                ListingSnapshot(
                    listing_id=listing.id,
                    snapshot_at=now,
                    raw_item_json=fields["raw_item_json"],
                )
            )
            target = listing
        analyze_listing(db, target)
        count += 1

    db.commit()
    logger.info("Ingest complete: %s item summaries processed", count)
    return count
