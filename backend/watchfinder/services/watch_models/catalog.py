"""Link listings to watch_models: match first, optional review queue, then create when allowed."""

from __future__ import annotations

from enum import Enum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from watchfinder.config import get_settings
from watchfinder.models import Listing, ListingEdit, WatchModel
from watchfinder.services.local_media import enrich_watch_model_image_from_listing
from watchfinder.services.valuation.effective import (
    effective_caliber,
    effective_model_family,
    effective_reference,
)
from watchfinder.services.watch_catalog_settings import get_watch_catalog_review_mode
from watchfinder.services.watch_catalog_settings import get_watch_catalog_queue_require_identity
from watchfinder.services.watch_models.candidates import rank_watch_model_candidates
from watchfinder.services.watch_models.link_review import (
    delete_pending_reviews_for_listing,
    upsert_pending_watch_link_review,
)
from watchfinder.services.watch_models.exclusions import (
    brand_is_catalog_excluded,
    catalog_excluded_brands,
)
from watchfinder.services.watch_models.match import (
    _find_by_brand_family,
    _find_by_brand_ref,
    try_auto_link_listing,
    try_exact_catalog_link,
)


class CatalogLinkOutcome(str, Enum):
    ALREADY_LINKED = "already_linked"
    LINKED_EXISTING = "linked_existing"
    CREATED_NEW = "created_new"
    SKIPPED_NO_IDENTITY = "skipped_no_identity"
    QUEUED_FOR_REVIEW = "queued_for_review"
    SKIPPED_EXCLUDED_BRAND = "skipped_excluded_brand"


def _title_snippet(title: str | None, max_len: int = 200) -> str | None:
    if not title or not title.strip():
        return None
    t = title.strip()
    return t if len(t) <= max_len else t[: max_len - 1] + "…"


def _insert_or_fetch_watch_model(db: Session, wm: WatchModel) -> tuple[WatchModel, bool]:
    """Persist new row or return existing. Second value is True if a new row was inserted."""
    if wm.reference and str(wm.reference).strip():
        existing = _find_by_brand_ref(db, wm.brand, str(wm.reference))
        if existing:
            return existing, False
        with db.begin_nested():
            try:
                db.add(wm)
                db.flush()
                return wm, True
            except IntegrityError:
                db.expunge(wm)
        got = _find_by_brand_ref(db, wm.brand, str(wm.reference))
        if got:
            return got, False
        raise RuntimeError("Could not insert or load watch_model for brand+reference")

    if wm.model_family and str(wm.model_family).strip():
        existing = _find_by_brand_family(db, wm.brand, str(wm.model_family))
        if existing:
            return existing, False
        db.add(wm)
        db.flush()
        return wm, True

    raise ValueError("watch model needs reference or model_family")


def _create_catalog_row_and_link_listing(
    db: Session,
    listing: Listing,
    parsed: dict[str, str],
    edit: ListingEdit | None,
) -> CatalogLinkOutcome:
    brand = (parsed.get("brand") or "").strip() or None
    if not brand:
        return CatalogLinkOutcome.SKIPPED_NO_IDENTITY
    excluded = catalog_excluded_brands(db)
    if brand_is_catalog_excluded(brand, excluded):
        return CatalogLinkOutcome.SKIPPED_EXCLUDED_BRAND
    ref, _ = effective_reference(parsed, edit)
    mf, _ = effective_model_family(parsed, edit)
    cal, _ = effective_caliber(parsed, edit)
    mf_clean = (mf or "").strip()

    if not ref and not mf_clean:
        return CatalogLinkOutcome.SKIPPED_NO_IDENTITY

    if ref:
        wm = _find_by_brand_ref(db, brand, ref)
        if wm is None:
            candidate = WatchModel(
                brand=brand,
                reference=ref.strip(),
                model_family=mf_clean or None,
                model_name=_title_snippet(listing.title),
                caliber=cal,
                image_urls=list(listing.image_urls) if listing.image_urls else None,
            )
            wm, created = _insert_or_fetch_watch_model(db, candidate)
        else:
            created = False
    else:
        wm = _find_by_brand_family(db, brand, mf_clean)
        if wm is None:
            candidate = WatchModel(
                brand=brand,
                reference=None,
                model_family=mf_clean,
                model_name=_title_snippet(listing.title),
                caliber=cal,
                image_urls=list(listing.image_urls) if listing.image_urls else None,
            )
            wm, created = _insert_or_fetch_watch_model(db, candidate)
        else:
            created = False

    listing.watch_model_id = wm.id
    return CatalogLinkOutcome.CREATED_NEW if created else CatalogLinkOutcome.LINKED_EXISTING


def ensure_watch_catalog_for_listing(
    db: Session,
    listing: Listing,
    parsed: dict[str, str],
    edit: ListingEdit | None,
    *,
    bypass_review: bool = False,
) -> CatalogLinkOutcome:
    """
    If bypass_review: always full auto (exact + fuzzy + create).
    Else if review mode: exact only; enqueue when identity exists but no exact link.
    Else: full auto.
    """
    review_on = get_watch_catalog_review_mode(db) == "review" and not bypass_review
    require_identity_for_queue = get_watch_catalog_queue_require_identity(db)

    if listing.watch_model_id is not None:
        delete_pending_reviews_for_listing(db, listing.id)
        return CatalogLinkOutcome.ALREADY_LINKED

    brand_check = (parsed.get("brand") or "").strip() or None
    excluded = catalog_excluded_brands(db)
    if brand_is_catalog_excluded(brand_check, excluded):
        delete_pending_reviews_for_listing(db, listing.id)
        return CatalogLinkOutcome.SKIPPED_EXCLUDED_BRAND

    if review_on:
        try_exact_catalog_link(db, listing, parsed, edit)
    else:
        try_auto_link_listing(db, listing, parsed, edit)

    if listing.watch_model_id is not None:
        delete_pending_reviews_for_listing(db, listing.id)
        return CatalogLinkOutcome.LINKED_EXISTING

    brand = (parsed.get("brand") or "").strip() or None
    if not brand:
        if review_on and not require_identity_for_queue:
            candidates = rank_watch_model_candidates(
                db,
                brand="",
                reference=None,
                model_family=None,
                title=listing.title,
            )
            upsert_pending_watch_link_review(db, listing, parsed, edit, candidates)
            return CatalogLinkOutcome.QUEUED_FOR_REVIEW
        return CatalogLinkOutcome.SKIPPED_NO_IDENTITY

    ref, _ = effective_reference(parsed, edit)
    mf, _ = effective_model_family(parsed, edit)
    mf_clean = (mf or "").strip()
    if not ref and not mf_clean:
        if review_on and not require_identity_for_queue:
            candidates = rank_watch_model_candidates(
                db,
                brand=brand,
                reference=None,
                model_family=None,
                title=listing.title,
            )
            upsert_pending_watch_link_review(db, listing, parsed, edit, candidates)
            return CatalogLinkOutcome.QUEUED_FOR_REVIEW
        return CatalogLinkOutcome.SKIPPED_NO_IDENTITY

    if review_on:
        candidates = rank_watch_model_candidates(
            db,
            brand=brand,
            reference=ref,
            model_family=mf_clean or None,
            title=listing.title,
        )
        upsert_pending_watch_link_review(db, listing, parsed, edit, candidates)
        return CatalogLinkOutcome.QUEUED_FOR_REVIEW

    return _create_catalog_row_and_link_listing(db, listing, parsed, edit)


def sync_unmatched_listings_watch_catalog(db: Session) -> dict[str, int]:
    """
    Re-analyze every active listing with no watch_model_id so catalog linking / match queue
    stays in sync (review mode enqueues; auto mode links or creates).
    """
    from sqlalchemy import select

    from watchfinder.services.pipeline.analyze import analyze_listing

    stats = {
        "scanned": 0,
        "already_linked": 0,
        "linked_existing": 0,
        "created_new": 0,
        "skipped_no_identity": 0,
        "queued_for_review": 0,
        "skipped_excluded_brand": 0,
    }
    stmt = (
        select(Listing.id)
        .where(Listing.is_active.is_(True), Listing.watch_model_id.is_(None))
        .order_by(Listing.last_seen_at.desc())
    )
    for lid in db.scalars(stmt).all():
        listing = db.get(Listing, lid)
        if not listing or listing.watch_model_id is not None:
            continue
        stats["scanned"] += 1
        out = analyze_listing(db, listing)
        if out == CatalogLinkOutcome.ALREADY_LINKED:
            stats["already_linked"] += 1
        elif out == CatalogLinkOutcome.LINKED_EXISTING:
            stats["linked_existing"] += 1
        elif out == CatalogLinkOutcome.CREATED_NEW:
            stats["created_new"] += 1
        elif out == CatalogLinkOutcome.QUEUED_FOR_REVIEW:
            stats["queued_for_review"] += 1
        elif out == CatalogLinkOutcome.SKIPPED_EXCLUDED_BRAND:
            stats["skipped_excluded_brand"] += 1
        else:
            stats["skipped_no_identity"] += 1
    return stats


def backfill_watch_catalog(db: Session) -> dict[str, int]:
    """Scan active listings; link or create catalog rows. Caller should commit."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from watchfinder.models import Listing, ListingEdit
    from watchfinder.services.market_snapshots import maybe_refresh_market_snapshots_for_model
    from watchfinder.services.watch_models import refresh_watch_model_observed_bounds

    stats = {
        "scanned": 0,
        "already_linked": 0,
        "linked_existing": 0,
        "created_new": 0,
        "skipped_no_identity": 0,
        "queued_for_review": 0,
        "skipped_excluded_brand": 0,
    }
    stmt = (
        select(Listing)
        .options(selectinload(Listing.parsed_attributes))
        .where(Listing.is_active.is_(True))
        .order_by(Listing.last_seen_at.desc())
    )
    for listing in db.scalars(stmt).all():
        stats["scanned"] += 1
        parsed = {a.key: (a.value_text or "") for a in listing.parsed_attributes}
        edit = db.get(ListingEdit, listing.id)
        out = ensure_watch_catalog_for_listing(db, listing, parsed, edit)
        if out == CatalogLinkOutcome.ALREADY_LINKED:
            stats["already_linked"] += 1
        elif out == CatalogLinkOutcome.LINKED_EXISTING:
            stats["linked_existing"] += 1
        elif out == CatalogLinkOutcome.CREATED_NEW:
            stats["created_new"] += 1
        elif out == CatalogLinkOutcome.QUEUED_FOR_REVIEW:
            stats["queued_for_review"] += 1
        elif out == CatalogLinkOutcome.SKIPPED_EXCLUDED_BRAND:
            stats["skipped_excluded_brand"] += 1
        else:
            stats["skipped_no_identity"] += 1
        if listing.watch_model_id is not None:
            refresh_watch_model_observed_bounds(db, listing.watch_model_id)
            enrich_watch_model_image_from_listing(db, listing, get_settings())
            maybe_refresh_market_snapshots_for_model(db, listing.watch_model_id, get_settings())
    return stats


def create_catalog_from_listing_identity(
    db: Session,
    listing: Listing,
    parsed: dict[str, str],
    edit: ListingEdit | None,
) -> CatalogLinkOutcome:
    """Force create/link from listing identity (used by review resolve 'create')."""
    return _create_catalog_row_and_link_listing(db, listing, parsed, edit)
