"""Assemble searchable text from a listing + raw item JSON."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from watchfinder.models import Listing


def _aspects_to_text(aspects: Any) -> str:
    if not aspects:
        return ""
    parts: list[str] = []
    if isinstance(aspects, list):
        for a in aspects:
            if not isinstance(a, dict):
                continue
            name = a.get("name") or a.get("localizedAspectName")
            val = a.get("value") or a.get("localizedAspectValues")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            if name and val:
                parts.append(f"{name}: {val}")
            elif name:
                parts.append(str(name))
    elif isinstance(aspects, dict):
        for k, v in aspects.items():
            parts.append(f"{k}: {v}")
    return " | ".join(parts)


def build_listing_corpus(listing: Listing) -> str:
    chunks: list[str] = []
    if listing.title:
        chunks.append(listing.title)
    if listing.subtitle:
        chunks.append(listing.subtitle)
    if listing.condition_description:
        chunks.append(listing.condition_description)
    if listing.category_path:
        chunks.append(listing.category_path)
    chunks.append(_aspects_to_text(listing.item_aspects))
    raw = listing.raw_item_json
    if isinstance(raw, dict):
        sd = raw.get("shortDescription")
        if sd:
            chunks.append(str(sd))
    return "\n".join(c for c in chunks if c).strip()


def corpus_preview(corpus: str, max_len: int = 2000) -> str:
    if len(corpus) <= max_len:
        return corpus
    return corpus[: max_len - 3] + "..."
