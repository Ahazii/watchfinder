"""Merge parsed listing attributes with ListingEdit overrides + source letters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchfinder.models import ListingEdit

# Shown in UI / API docs
SOURCE_LEGEND: dict[str, str] = {
    "M": "Manual — you entered this",
    "I": "Inferred — AI / heuristic (not yet wired for all fields)",
    "S": "Searched — matched via external or eBay search workflow",
    "R": "Rules — parsed from title/description by WatchFinder",
    "O": "Observed — captured from ingest when listing state changed",
    "H": "Historical — derived from your past sale records in this database",
    "P": "Parsed — synonym for rules-based text extraction",
}


def norm_key(s: str | None) -> str | None:
    if not s or not str(s).strip():
        return None
    return str(s).strip().lower()


def effective_model_family(
    parsed: dict[str, str], edit: ListingEdit | None
) -> tuple[str | None, str]:
    if edit and (edit.model_family or "").strip():
        return edit.model_family.strip(), (edit.model_family_source or "M")
    # optional future: parse model_family from title
    return None, ""


def effective_reference(
    parsed: dict[str, str], edit: ListingEdit | None
) -> tuple[str | None, str]:
    if edit and (edit.reference_text or "").strip():
        return edit.reference_text.strip(), (edit.reference_source or "M")
    if parsed.get("reference"):
        return parsed["reference"], "R"
    return None, ""


def effective_caliber(
    parsed: dict[str, str], edit: ListingEdit | None
) -> tuple[str | None, str]:
    if edit and (edit.caliber_text or "").strip():
        return edit.caliber_text.strip(), (edit.caliber_source or "M")
    if parsed.get("caliber"):
        return parsed["caliber"], "R"
    return None, ""
