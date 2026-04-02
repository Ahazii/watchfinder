"""Scheduled ingestion: Browse search → upsert listings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import Listing, ListingSnapshot
from watchfinder.services.ebay import EbayAuthClient, EbayBrowseClient
from watchfinder.services.ebay.api_usage import increment_browse_search
from watchfinder.services.ingestion.mapper import item_summary_to_listing_fields
from watchfinder.services.ingest_settings import (
    get_ingest_search_limit,
    resolve_ingest_query_strings,
)
from watchfinder.services.pipeline import analyze_listing

logger = logging.getLogger(__name__)


def run_browse_ingest(
    db: Session,
    settings: Settings | None = None,
    *,
    search_query: str | None = None,
) -> int:
    """
    Run one Browse search page and upsert listings.
    Returns number of item summaries processed.
    """
    settings = settings or get_settings()
    q = (search_query if search_query is not None else settings.ebay_search_query).strip()
    if not q:
        logger.warning("Ingest skipped: empty search query")
        return 0

    auth = EbayAuthClient(settings, db)
    browse = EbayBrowseClient(settings, auth)

    data = browse.search(
        q,
        limit=get_ingest_search_limit(db, settings),
        offset=0,
    )
    increment_browse_search(db)
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
    logger.info("Ingest complete for %r: %s item summaries processed", q, count)
    return count


def run_all_browse_ingest(db: Session, settings: Settings | None = None) -> int:
    """
    Run Browse ingest for each enabled query (DB saved lines), or env fallback.
    Returns total item summaries processed across all queries.
    """
    settings = settings or get_settings()
    queries = resolve_ingest_query_strings(db, settings)
    if not queries:
        logger.warning("Ingest skipped: no queries configured")
        return 0
    total = 0
    for query in queries:
        total += run_browse_ingest(db, settings, search_query=query)
    logger.info(
        "Ingest cycle complete: %s summaries across %s query/queries",
        total,
        len(queries),
    )
    return total
