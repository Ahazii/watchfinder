"""Rules-first extraction of brand, reference, movement, caliber from corpus text."""

from __future__ import annotations

import re

from watchfinder.services.parsing.keywords import KNOWN_BRANDS, MOVEMENT_HINTS


# Reference-like: 4–6 digit refs, optional letter suffix, or common Ref. prefix
REF_PATTERN = re.compile(
    r"\b(?:ref\.?\s*)?(\d{3,6}[a-z]{0,3})\b",
    re.IGNORECASE,
)

# Known caliber mentions
CALIBER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("eta_2824", re.compile(r"\beta\s*2824[-\d]*\b", re.I)),
    ("eta_2892", re.compile(r"\beta\s*2892[-\d]*\b", re.I)),
    ("eta_7750", re.compile(r"\beta\s*7750\b", re.I)),
    ("sellita_sw200", re.compile(r"\bsellita\s*sw200\b", re.I)),
    ("sellita_sw500", re.compile(r"\bsellita\s*sw500\b", re.I)),
    ("miyota_8215", re.compile(r"\bmiyota\s*8215\b", re.I)),
    ("miyota_9015", re.compile(r"\bmiyota\s*9015\b", re.I)),
    ("nh35", re.compile(r"\bnh35[a-z]?\b", re.I)),
    ("nh36", re.compile(r"\bnh36[a-z]?\b", re.I)),
    ("7s26", re.compile(r"\b7s26\b", re.I)),
    ("4r36", re.compile(r"\b4r36\b", re.I)),
    ("valjoux_7750", re.compile(r"\bvaljoux\s*7750\b", re.I)),
]


def extract_brand(corpus_lower: str, title_lower: str) -> str | None:
    hay = f"{title_lower} {corpus_lower}"
    for b in sorted(KNOWN_BRANDS, key=len, reverse=True):
        if b in hay:
            return b.title() if b != "iwc" else "IWC"
    return None


def extract_reference(corpus: str) -> str | None:
    m = REF_PATTERN.search(corpus)
    if m:
        return m.group(1).upper()
    return None


def extract_movement(corpus_lower: str) -> str | None:
    for hint in sorted(MOVEMENT_HINTS, key=len, reverse=True):
        if hint in corpus_lower:
            return hint
    return None


def extract_caliber(corpus: str) -> str | None:
    for name, pat in CALIBER_PATTERNS:
        if pat.search(corpus):
            return name.replace("_", " ").upper()
    return None


def extract_running_state(corpus_lower: str) -> str | None:
    if any(
        x in corpus_lower
        for x in (
            "not running",
            "non running",
            "doesn't run",
            "does not run",
            "not working",
            "won't run",
            "stopped",
        )
    ):
        return "non_runner"
    if "untested" in corpus_lower or "sold as is" in corpus_lower:
        return "unknown"
    if "runs well" in corpus_lower or "keeping time" in corpus_lower:
        return "running"
    return None


def parse_watch_attributes(listing_title: str | None, corpus: str) -> dict[str, str]:
    """Return flat map for ParsedAttribute rows (namespace watch)."""
    title = listing_title or ""
    corpus_lower = corpus.lower()
    title_lower = title.lower()
    out: dict[str, str] = {}
    brand = extract_brand(corpus_lower, title_lower)
    if brand:
        out["brand"] = brand
    ref = extract_reference(corpus)
    if ref:
        out["reference"] = ref
    mov = extract_movement(corpus_lower)
    if mov:
        out["movement"] = mov
    cal = extract_caliber(corpus)
    if cal:
        out["caliber"] = cal
    rs = extract_running_state(corpus_lower)
    if rs:
        out["running_state"] = rs
    return out
