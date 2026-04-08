"""Debug-only HTML inspection for Everywatch import experiments (not used in scoring)."""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from watchfinder.config import Settings, get_settings
from watchfinder.services.everywatch_client import (
    fetch_everywatch_page,
    is_everywatch_watch_detail_url,
    parse_watch_detail_hit,
    parse_watch_hits_from_html,
)


def analyze_everywatch_html(html: str, page_url: str) -> dict[str, Any]:
    """Structured fields to compare with watch_models columns / plan mapping."""
    soup = BeautifulSoup(html, "html.parser")
    og: dict[str, str | None] = {}
    for tag in soup.select('meta[property^="og:"]'):
        prop = tag.get("property")
        if prop:
            og[str(prop)] = tag.get("content")
    h1 = soup.find("h1")
    title_el = soup.find("title")
    ldjson_blocks: list[dict[str, Any]] = []
    for s in soup.find_all(
        "script", type=lambda t: bool(t and "ld+json" in str(t).lower())
    ):
        raw = (s.string or s.get_text() or "").strip()
        preview = raw[:600]
        parsed_ok = False
        try:
            json.loads(raw)
            parsed_ok = True
        except json.JSONDecodeError:
            pass
        ldjson_blocks.append(
            {"length": len(raw), "preview": preview, "valid_json": parsed_ok}
        )
    watch_hrefs: list[str] = []
    for a in soup.select('a[href*="watch-"]'):
        href = (a.get("href") or "").strip()
        if href and href not in watch_hrefs:
            watch_hrefs.append(href.split("?", 1)[0])
        if len(watch_hrefs) >= 40:
            break
    data_attrs_sample: list[str] = []
    for el in soup.select("[data-testid],[data-id],[data-slug],[data-watch]")[:25]:
        keys = [f"{k}={v!r}" for k, v in el.attrs.items() if k.startswith("data-")]
        if keys:
            data_attrs_sample.append(f"{el.name}: " + " ".join(keys[:4]))
    parsed_hits = parse_watch_hits_from_html(html, page_url=page_url)
    detail_import_preview: dict[str, Any] | None = None
    if is_everywatch_watch_detail_url(page_url):
        detail_import_preview = parse_watch_detail_hit(html, page_url=page_url)
    return {
        "page_url": page_url,
        "html_length": len(html),
        "title_tag": (title_el.get_text() if title_el else "").strip() or None,
        "h1_text": h1.get_text(" ", strip=True) if h1 else None,
        "og_tags": og,
        "json_ld_block_count": len(ldjson_blocks),
        "json_ld_previews": ldjson_blocks[:6],
        "script_tags_total": len(soup.find_all("script")),
        "sample_watch_hrefs": watch_hrefs[:25],
        "data_attribute_samples": data_attrs_sample[:20],
        "parsed_listing_hits_count": len(parsed_hits),
        "parsed_listing_hits_sample": parsed_hits[:15],
        "detail_import_preview": detail_import_preview,
    }


def run_everywatch_debug_fetches(
    urls: list[str],
    *,
    settings: Settings | None = None,
    cookie_header: str | None = None,
    auth_headers: dict[str, str] | None = None,
    max_urls: int = 14,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    extra: dict[str, str] = {}
    if auth_headers:
        extra.update({k: v for k, v in auth_headers.items() if v})
    if cookie_header and cookie_header.strip():
        extra["Cookie"] = cookie_header.strip()[:8000]
    out: list[dict[str, Any]] = []
    for url in urls[:max_urls]:
        u = (url or "").strip()
        if not u:
            continue
        html, err, code = fetch_everywatch_page(
            u, settings=settings, extra_headers=extra or None
        )
        row: dict[str, Any] = {
            "url": u,
            "status_code": code,
            "error": err,
            "html_received": html is not None,
            "analysis": None,
        }
        if html:
            row["analysis"] = analyze_everywatch_html(html, page_url=u)
        out.append(row)
    return out
