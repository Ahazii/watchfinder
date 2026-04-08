"""Catalog brand exclusions (WATCH_CATALOG_EXCLUDED_BRANDS)."""

from __future__ import annotations

from watchfinder.config import Settings


def parse_excluded_brand_names(raw: str | None) -> frozenset[str]:
    if not raw or not str(raw).strip():
        return frozenset()
    out: list[str] = []
    for part in str(raw).split(","):
        t = part.strip().lower()
        if t:
            out.append(t)
    return frozenset(out)


def catalog_excluded_brands(settings: Settings) -> frozenset[str]:
    return parse_excluded_brand_names(settings.watch_catalog_excluded_brands)


def brand_is_catalog_excluded(brand: str | None, excluded: frozenset[str]) -> bool:
    if not brand or not excluded:
        return False
    return brand.strip().lower() in excluded
