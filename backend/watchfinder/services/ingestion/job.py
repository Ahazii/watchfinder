"""Scheduled ingestion: Browse search → upsert listings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import Listing, ListingSnapshot, NotInterestedListing
from watchfinder.services.ebay import EbayAuthClient, EbayBrowseClient
from watchfinder.services.ebay.api_usage import increment_browse_search
from watchfinder.services.ingestion.mapper import item_summary_to_listing_fields
from watchfinder.services.listing_exclusions import (
    listing_excluded_terms,
    listing_fields_match_excluded_terms,
)
from watchfinder.services.listing_status import compute_is_effectively_active
from watchfinder.services.ingest_settings import (
    get_ingest_max_pages,
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
    browse: EbayBrowseClient | None = None,
) -> int:
    """
    Run Browse search for one query line (up to ``ingest_max_pages`` offset pages).
    Returns number of item summaries processed.

    Pass a shared ``browse`` client from ``run_all_browse_ingest`` so OAuth token
    is reused across query lines (one token refresh per cycle, not per line).
    """
    settings = settings or get_settings()
    q = (search_query if search_query is not None else settings.ebay_search_query).strip()
    if not q:
        logger.warning("Ingest skipped: empty search query")
        return 0

    if browse is None:
        auth = EbayAuthClient(settings, db)
        browse = EbayBrowseClient(settings, auth)

    limit = get_ingest_search_limit(db, settings)
    max_pages = get_ingest_max_pages(db, settings)
    now = datetime.now(UTC)
    count = 0
    pages_done = 0
    skipped_excluded = 0
    deactivated_excluded = 0
    excluded_terms = listing_excluded_terms(db, settings)

    for page_idx in range(max_pages):
        data = browse.search(q, limit=limit, offset=page_idx * limit)
        increment_browse_search(db)
        summaries = data.get("itemSummaries") or []
        if not summaries:
            break
        pages_done = page_idx + 1

        for raw in summaries:
            if not isinstance(raw, dict):
                continue
            try:
                fields = item_summary_to_listing_fields(raw)
            except ValueError as e:
                logger.warning("Skip summary: %s", e)
                continue

            ebay_id = fields["ebay_item_id"]
            is_blocked = db.execute(
                select(NotInterestedListing.id).where(
                    NotInterestedListing.ebay_item_id == ebay_id,
                    NotInterestedListing.is_active.is_(True),
                )
            ).scalar_one_or_none()
            if is_blocked:
                continue
            existing = db.execute(
                select(Listing).where(Listing.ebay_item_id == ebay_id)
            ).scalar_one_or_none()
            excluded_term = listing_fields_match_excluded_terms(fields, excluded_terms)
            if excluded_term:
                skipped_excluded += 1
                if existing and existing.is_active:
                    existing.is_active = False
                    existing.last_seen_at = now
                    deactivated_excluded += 1
                continue

            if existing:
                for k, v in fields.items():
                    if k in ("ebay_item_id", "first_seen_at"):
                        continue
                    setattr(existing, k, v)
                existing.last_seen_at = now
                existing.is_active = compute_is_effectively_active(existing.listing_ended_at, now=now)
                db.add(
                    ListingSnapshot(
                        listing_id=existing.id,
                        snapshot_at=now,
                        raw_item_json=fields["raw_item_json"],
                    )
                )
                target = existing
            else:
                listing = Listing(
                    **fields,
                    first_seen_at=now,
                    last_seen_at=now,
                    is_active=compute_is_effectively_active(fields.get("listing_ended_at"), now=now),
                )
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

        if len(summaries) < limit:
            break

    db.commit()
    logger.info(
        "Ingest complete for %r: %s item summaries (%s page(s), limit=%s)",
        q,
        count,
        pages_done,
        limit,
    )
    if skipped_excluded:
        logger.info(
            "Ingest exclusions for %r: skipped=%s deactivated_existing=%s",
            q,
            skipped_excluded,
            deactivated_excluded,
        )
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
    auth = EbayAuthClient(settings, db)
    browse = EbayBrowseClient(settings, auth)
    total = 0
    for query in queries:
        total += run_browse_ingest(
            db, settings, search_query=query, browse=browse
        )
    logger.info(
        "Ingest cycle complete: %s summaries across %s query/queries",
        total,
        len(queries),
    )
    return total
