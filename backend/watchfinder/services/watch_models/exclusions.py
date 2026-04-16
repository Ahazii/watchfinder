"""Catalog brand exclusions (env WATCH_CATALOG_EXCLUDED_BRANDS + Settings UI app_settings)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import AppSetting, Listing
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
    if not brand or not excluded:
        return False
    return brand.strip().lower() in excluded


def listing_matches_catalog_brand_exclusion(
    listing: Listing,
    parsed: dict[str, str],
    excluded: frozenset[str],
) -> bool:
    """
    True if parsed brand is excluded (exact) or any exclusion term appears in title/subtitle.
    Substring match on title is case-insensitive; terms shorter than 2 chars are ignored for title scan.
    """
    if not excluded:
        return False
    brand = (parsed.get("brand") or "").strip() or None
    if brand_is_catalog_excluded(brand, excluded):
        return True
    hay = f"{listing.title or ''} {listing.subtitle or ''}".lower()
    for term in excluded:
        t = (term or "").strip().lower()
        if len(t) < 2:
            continue
        if t in hay:
            return True
    return False
