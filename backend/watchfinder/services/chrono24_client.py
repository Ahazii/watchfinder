"""Chrono24: search URLs for operators; automated HTML fetch usually returns 403 outside a browser."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

import httpx

from watchfinder.config import Settings, get_settings
logger = logging.getLogger(__name__)
_DEFAULT_UA = "WatchFinder/1.0 (private catalog; occasional on-demand page fetch)"


def chrono24_search_url(query: str, *, uk: bool = True) -> str:
    base = "https://www.chrono24.co.uk" if uk else "https://www.chrono24.com"
    return f"{base}/search/index.htm?dosearch=true&query={quote_plus(query.strip())}"


def chrono24_google_site_url(query: str) -> str:
    q = f"site:chrono24.co.uk {query.strip()}"
    return f"https://www.google.com/search?q={quote_plus(q)}"


def try_fetch_chrono24_search(
    query: str,
    settings: Settings | None = None,
    *,
    timeout: float = 22.0,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Attempt to load search HTML and extract minimal hits. Often **403** from Chrono24 for server clients.
    """
    settings = settings or get_settings()
    ua = settings.watchbase_import_user_agent or _DEFAULT_UA
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    url = chrono24_search_url(query, uk=True)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            if r.status_code == 403:
                return [], "HTTP 403 (Chrono24 often blocks non-browser clients; use search URL in a browser)."
            r.raise_for_status()
            text = r.text
    except httpx.HTTPError as e:
        logger.warning("Chrono24 search failed: %s", e)
        return [], str(e)

    hits: list[dict[str, Any]] = []
    # Light-weight: __NEXT_DATA__ JSON (when present and not blocked)
    import json
    import re

    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        text,
        re.DOTALL,
    )
    if not m:
        return hits, None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return hits, None

    def walk(o: Any, depth: int = 0) -> None:
        if depth > 14 or len(hits) >= 25:
            return
        if isinstance(o, dict):
            u = o.get("url") or o.get("listingUrl") or o.get("detailUrl")
            title = o.get("title") or o.get("name") or o.get("heading")
            price = o.get("price") or o.get("formattedPrice") or o.get("listingPrice")
            if u and isinstance(u, str) and "chrono24" in u.lower() and "/watch/" in u.lower():
                label = f"{title or ''} {price or ''}".strip() or u
                hits.append({"url": u.split("?", 1)[0], "label": label[:400]})
            for v in o.values():
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)

    walk(data)
    return hits, None
