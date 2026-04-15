"""Listing exclusion keyword matching and bulk inactive apply."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import AppSetting, Listing
from watchfinder.services.watch_catalog_settings import KEY_EXCLUDED_BRANDS


def parse_excluded_terms(raw: str | None) -> tuple[str, ...]:
    if not raw or not str(raw).strip():
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for part in str(raw).split(","):
        t = part.strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return tuple(out)


def listing_excluded_terms(
    db: Session, settings: Settings | None = None
) -> tuple[str, ...]:
    """Union of env and app_settings exclusion terms."""
    settings = settings or get_settings()
    from_env = parse_excluded_terms(settings.watch_catalog_excluded_brands)
    row = db.get(AppSetting, KEY_EXCLUDED_BRANDS)
    from_db = parse_excluded_terms(row.value_text if row else None)
    return tuple(dict.fromkeys([*from_env, *from_db]))


def _collect_text_fragments(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        text = value.strip()
        if text:
            yield text
        return
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _collect_text_fragments(k)
            yield from _collect_text_fragments(v)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _collect_text_fragments(item)


def listing_texts_from_fields(fields: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for val in fields.values():
        texts.extend(_collect_text_fragments(val))
    return texts


def listing_texts_from_model(listing: Listing) -> list[str]:
    data = {
        "ebay_item_id": listing.ebay_item_id,
        "title": listing.title,
        "subtitle": listing.subtitle,
        "web_url": listing.web_url,
        "currency": listing.currency,
        "seller_username": listing.seller_username,
        "condition_description": listing.condition_description,
        "category_path": listing.category_path,
        "buying_options": listing.buying_options,
        "item_aspects": listing.item_aspects,
        "raw_item_json": listing.raw_item_json,
    }
    return listing_texts_from_fields(data)


def find_matching_excluded_term(
    texts: Iterable[str], excluded_terms: tuple[str, ...]
) -> str | None:
    if not excluded_terms:
        return None
    haystack = "\n".join(t.lower() for t in texts if t)
    if not haystack:
        return None
    for term in excluded_terms:
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            return term
    return None


def listing_fields_match_excluded_terms(
    fields: dict[str, Any], excluded_terms: tuple[str, ...]
) -> str | None:
    return find_matching_excluded_term(
        listing_texts_from_fields(fields),
        excluded_terms,
    )


def listing_model_matches_excluded_terms(
    listing: Listing, excluded_terms: tuple[str, ...]
) -> str | None:
    return find_matching_excluded_term(
        listing_texts_from_model(listing),
        excluded_terms,
    )


def apply_excluded_terms_to_all_listings(
    db: Session, settings: Settings | None = None
) -> dict[str, int]:
    excluded_terms = listing_excluded_terms(db, settings)
    scanned = matched = updated = 0
    now = datetime.now(UTC)
    if not excluded_terms:
        return {"scanned": 0, "matched": 0, "updated": 0}
    for listing in db.scalars(select(Listing)).all():
        scanned += 1
        if not listing_model_matches_excluded_terms(listing, excluded_terms):
            continue
        matched += 1
        if listing.is_active:
            listing.is_active = False
            listing.last_seen_at = now
            updated += 1
    db.commit()
    return {"scanned": scanned, "matched": matched, "updated": updated}
