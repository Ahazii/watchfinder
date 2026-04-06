"""Parse WatchBase filter JSON (`/filter/results?q=`) into structured watch links (no DB)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from watchfinder.services.watchbase_path import WATCHBASE_HOSTS, canonical_watch_url

logger = logging.getLogger(__name__)


def parse_watches_from_filter_json(data: dict[str, Any]) -> list[dict[str, str]]:
    """
    Extract watch page URLs + labels from the **watchesHtml** field in filter/results JSON.
    Skips placeholder blocks and non-watch links.
    """
    html = data.get("watchesHtml") or ""
    if not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for a in soup.select("a.item-block.watch-block[href]"):
        if "dummy" in (a.get("class") or []):
            continue
        raw_href = (a.get("href") or "").strip()
        if not raw_href:
            continue
        if raw_href.startswith("//"):
            href = "https:" + raw_href
        elif raw_href.startswith("/"):
            href = "https://watchbase.com" + raw_href.split("?", 1)[0]
        elif raw_href.startswith("http"):
            href = raw_href.split("?", 1)[0]
        else:
            continue

        try:
            host = urlparse(href).netloc.lower()
        except Exception:
            continue
        if host not in WATCHBASE_HOSTS and not host.endswith(".watchbase.com"):
            continue
        if "/caliber/" in href:
            continue

        path = urlparse(href).path.rstrip("/")
        if path.count("/") < 3:
            continue

        if href in seen:
            continue
        seen.add(href)

        label_parts: list[str] = []
        top = a.select_one(".toptext")
        if top:
            label_parts.append(top.get_text(" ", strip=True))
        bottom = a.select_one(".bottomtext")
        if bottom:
            label_parts.append(bottom.get_text(" ", strip=True))
        img = a.find("img", alt=True)
        if img and img.get("alt"):
            alt = str(img["alt"]).strip()
            if alt and alt not in " ".join(label_parts):
                label_parts.append(alt)
        label = " — ".join(p for p in label_parts if p) or path

        items.append({"url": canonical_watch_url(path), "label": label})

    return items
