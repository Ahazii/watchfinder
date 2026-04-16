"""Catalog brand exclusions (env WATCH_CATALOG_EXCLUDED_BRANDS + Settings UI app_settings)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import AppSetting, Listing
from watchfinder.services.listing_exclusions import listing_texts_from_model
from watchfinder.services.watch_catalog_settings import KEY_EXCLUDED_BRANDS


def parse_excluded_brand_names(raw: str | None) -> frozenset[str]:
    if not raw or not str(raw).strip():
        return frozenset()
    out: list[str] = []
    for part in str(raw).split(","):
        t = part.strip().lower()
        if t:
            out.append(t)
    return frozenset(out)


def catalog_excluded_brands(db: Session, settings: Settings | None = None) -> frozenset[str]:
    """
    Union of env-based names and persisted Settings UI list (both apply).
    """
    settings = settings or get_settings()
    from_env = parse_excluded_brand_names(settings.watch_catalog_excluded_brands)
    row = db.get(AppSetting, KEY_EXCLUDED_BRANDS)
    from_db = parse_excluded_brand_names(row.value_text if row else None)
    return frozenset(from_env | from_db)


def brand_is_catalog_excluded(brand: str | None, excluded: frozenset[str]) -> bool:
    """
    True if the brand string equals an excluded term (exact) or contains an excluded term as substring.
    Substring match avoids misses when parsed brand is e.g. \"Nintendo Game Watch\" but the list only has \"nintendo\".
    """
    if not brand or not excluded:
        return False
    bl = brand.strip().lower()
    if bl in excluded:
        return True
    for term in excluded:
        t = (term or "").strip().lower()
        if len(t) >= 2 and t in bl:
            return True
    return False


def _listing_exclusion_haystack(listing: Listing, parsed: dict[str, str]) -> str:
    """
    Lowercased searchable blob: same deep text as ingest exclusions (title, raw JSON, aspects, etc.)
    plus current parse pass values. Brand names often live only under raw_item_json / shortDescription.
    """
    texts = listing_texts_from_model(listing)
    texts.extend(str(v) for v in parsed.values() if v)
    return "\n".join(t.lower() for t in texts if t)


def listing_matches_catalog_brand_exclusion(
    listing: Listing,
    parsed: dict[str, str],
    excluded: frozenset[str],
) -> bool:
    """
    True if any exclusion term matches parsed brand (exact or substring) or appears anywhere in
    title, subtitle, condition, category, item_aspects, or parsed attribute values (substring, case-insensitive).
    Terms shorter than 2 characters are skipped.
    """
    if not excluded:
        return False
    brand = (parsed.get("brand") or "").strip() or None
    if brand_is_catalog_excluded(brand, excluded):
        return True
    hay = _listing_exclusion_haystack(listing, parsed)
    for term in excluded:
        t = (term or "").strip().lower()
        if len(t) < 2:
            continue
        if t in hay:
            return True
    return False
