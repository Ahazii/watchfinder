"""Build WatchBase watch page path from URL or brand + family + reference."""

from __future__ import annotations

import re
from urllib.parse import urlparse

WATCHBASE_HOSTS = frozenset({"watchbase.com", "www.watchbase.com"})
WATCHBASE_ORIGIN = "https://watchbase.com"


def slugify_segment(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "watch"


def path_from_watchbase_url(url: str) -> str | None:
    """Return path like /omega/seamaster-diver-300m/210-30-42-20-01-001 or None."""
    raw = (url or "").replace("\u00a0", " ").strip()
    if not raw:
        return None
    # Paste without scheme: watchbase.com/omega/...
    low = raw.lower()
    if "://" not in raw and (low.startswith("watchbase.com/") or low.startswith("www.watchbase.com/")):
        raw = "https://" + raw.split("?", 1)[0].split("#", 1)[0]
    # Path-only: /omega/seamaster-diver-300m/ref-slug
    elif "://" not in raw and raw.startswith("/"):
        path_only = raw.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        if path_only.count("/") >= 3:
            raw = f"{WATCHBASE_ORIGIN}{path_only}"
    p = urlparse(raw)
    if p.scheme not in ("http", "https"):
        return None
    if p.netloc.lower() not in WATCHBASE_HOSTS:
        return None
    path = p.path.rstrip("/")
    if not path or path.count("/") < 3:
        return None
    if path.endswith("/prices"):
        path = path[: -len("/prices")]
    return path or None


def guessed_watch_path(brand: str, family: str, reference: str) -> str | None:
    b = (brand or "").strip()
    f = (family or "").strip()
    r = (reference or "").strip()
    if not b or not f or not r:
        return None
    ref_slug = r.replace(".", "-")
    if not ref_slug:
        return None
    return f"/{slugify_segment(b)}/{slugify_segment(f)}/{ref_slug}"


def canonical_watch_url(path: str) -> str:
    return f"{WATCHBASE_ORIGIN}{path.rstrip('/')}"
