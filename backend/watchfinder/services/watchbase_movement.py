"""Extract caliber designation from WatchBase **Movement** table cell (link + text)."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


def _caliber_slug_from_href(href: str) -> str | None:
    href = (href or "").strip().split("?")[0].rstrip("/")
    if "/caliber/" not in href.lower():
        return None
    part = href.lower().split("/caliber/")[-1]
    if not part or part in ("/", ""):
        return None
    # Single segment or last segment: .../caliber/8800 or .../caliber/3235
    slug = part.split("/")[-1]
    return slug.strip() or None


def caliber_from_movement_td(td: Any) -> str | None:
    """
    Prefer caliber id from link to ``/caliber/…``; else regex ``caliber <token>`` / ``cal. <token>``.
    """
    if td is None:
        return None
    for a in td.find_all("a", href=True):
        slug = _caliber_slug_from_href(str(a.get("href", "")))
        if slug:
            return slug
    text = " ".join(td.get_text().split())
    if not text:
        return None
    m = re.search(r"(?i)\bcaliber\s+([A-Za-z0-9][A-Za-z0-9./+\-]*)", text)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"(?i)\bcal\.?\s+([A-Za-z0-9][A-Za-z0-9./+\-]*)", text)
    if m2:
        return m2.group(1).strip()
    return None


def caliber_from_watchbase_watch_html(html: str) -> str | None:
    """Find the Movement row in ``table.info-table`` and return a short caliber string."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.select("table.info-table"):
        for tr in table.find_all("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if not th or not td:
                continue
            key = th.get_text(strip=True).rstrip(":").strip()
            if key == "Movement":
                return caliber_from_movement_td(td)
    return None
