"""Heuristic listing type: complete watch vs movement-only vs other parts."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchfinder.models import Listing

# Strong phrases → movement / donor listing (not a cased watch)
_MOVEMENT_STRONG = (
    "movement only",
    "caliber only",
    "calibre only",
    "mouvement seul",
    "mouvement only",
    "uhrwerk nur",
    "werk only",
    "donor movement",
    "for parts movement",
    "spare movement",
    "watch movement for parts",
)

_MOVEMENT_MEDIUM = (
    "no case",
    "no dial",
    "no hands",
    "ohne gehäuse",
    "sans boîtier",
    "movement for sale",
    "uhrwerk",
    "werk ",
    " eta 28",
    " eta 27",
    " valjoux",
    " unitas",
    " lemania",
    " zenith el",
)

# Parts (not whole watch, not raw movement block)
_PARTS_STRONG = (
    "dial only",
    "zifferblatt nur",
    "hands only",
    "hands set",
    "zeiger",
    "case only",
    "gehäuse only",
    "bezel only",
    "bracelet only",
    "band only",
    "buckle only",
    "crown only",
    "crystal only",
    "glass only",
    "rotor only",
    "stem only",
    "chapter ring",
)

_PARTS_MEDIUM = (
    "for parts",
    "spare parts",
    "ersatzteil",
    "repair parts",
)

# Whole-watch signals
_WATCH_STRONG = (
    "complete watch",
    "full watch",
    "wristwatch",
    "wrist watch",
    " men's watch",
    " mens watch",
    " ladies watch",
    " damenuhr",
    " herrenuhr",
    "box and papers",
    "box & papers",
    "full set",
    "unworn",
)

_CATEGORY_PARTS_HINT = re.compile(
    r"watch\s+parts|parts\s*&\s*accessories|jewelry\s*&\s*watches.*parts",
    re.I,
)


def _text_blob(listing: Listing | None, title: str | None, corpus: str, parsed: dict[str, str]) -> str:
    parts: list[str] = []
    if title:
        parts.append(title)
    parts.append(corpus)
    if listing and listing.category_path:
        parts.append(listing.category_path)
    cal = (parsed.get("caliber") or "").strip()
    if cal:
        parts.append(cal)
    return "\n".join(parts).lower()


def infer_listing_type(
    listing: Listing | None,
    title: str | None,
    corpus: str,
    parsed: dict[str, str],
) -> str:
    """
    Return one of: watch_complete, movement_only, parts_other, unknown.
    Conservative: unknown when signals conflict or are weak.
    """
    blob = _text_blob(listing, title, corpus, parsed)

    m_score = 0
    for s in _MOVEMENT_STRONG:
        if s in blob:
            m_score += 4
    for s in _MOVEMENT_MEDIUM:
        if s in blob:
            m_score += 2

    p_score = 0
    for s in _PARTS_STRONG:
        if s in blob:
            p_score += 4
    for s in _PARTS_MEDIUM:
        if s in blob:
            p_score += 1

    w_score = 0
    for s in _WATCH_STRONG:
        if s in blob:
            w_score += 3
    # Typical full-listing cues
    if re.search(r"\b(41mm|40mm|36mm|39mm|42mm|38mm)\b", blob):
        w_score += 1
    if "box" in blob and "paper" in blob:
        w_score += 2

    if listing and listing.category_path and _CATEGORY_PARTS_HINT.search(listing.category_path):
        p_score += 2

    # Conflicts: do not guess
    if m_score >= 4 and w_score >= 4:
        return "unknown"
    if p_score >= 4 and w_score >= 4:
        return "unknown"

    if m_score >= 4 and m_score >= p_score + 2:
        return "movement_only"
    if p_score >= 4 and p_score >= m_score:
        return "parts_other"
    if w_score >= 3 and w_score >= m_score and w_score >= p_score:
        return "watch_complete"

    if m_score >= 2 and m_score > p_score and m_score > w_score:
        return "movement_only"
    if p_score >= 2 and p_score > m_score and p_score > w_score:
        return "parts_other"

    return "unknown"


def maybe_apply_auto_listing_type(
    listing: Listing,
    corpus: str,
    parsed: dict[str, str],
) -> None:
    """If listing is not manually classified, set listing_type from heuristics."""
    src = (getattr(listing, "listing_type_source", None) or "auto").strip().lower()
    if src == "manual":
        return
    inferred = infer_listing_type(listing, listing.title, corpus, parsed)
    listing.listing_type = inferred
