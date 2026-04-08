"""Fetch Everywatch model listing pages and extract watch rows + prices (best-effort HTML parse)."""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from bs4 import BeautifulSoup

from watchfinder.config import Settings, get_settings

logger = logging.getLogger(__name__)

EVERYWATCH_ORIGIN = "https://everywatch.com"
_DEFAULT_UA = "WatchFinder/1.0 (private catalog; occasional on-demand page fetch)"

_PRICE_RE = re.compile(
    r"([\d][\d,]*(?:\.\d+)?)\s*(USD|EUR|GBP)\b",
    re.IGNORECASE,
)


def slugify_segment(s: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "-", (s or "").strip().lower()).strip("-")
    return t or "watch"


def reference_alnum(ref: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", (ref or "").strip())


def candidate_model_urls(brand: str, reference: str | None, model_family: str | None) -> list[str]:
    """Ordered URLs to try for a model / reference listing page."""
    b = slugify_segment(brand)
    out: list[str] = []
    ref_key = reference_alnum(reference or "")
    if b and ref_key:
        out.append(f"{EVERYWATCH_ORIGIN}/{b}/{ref_key.lower()}")
    if b and model_family and (model_family or "").strip():
        fam = slugify_segment(model_family)
        if fam and f"{EVERYWATCH_ORIGIN}/{b}/{fam}" not in out:
            out.append(f"{EVERYWATCH_ORIGIN}/{b}/{fam}")
    return out


def _abs_url(href: str) -> str | None:
    if not href or not href.strip():
        return None
    href = href.strip()
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return EVERYWATCH_ORIGIN.rstrip("/") + href
    if href.startswith("http"):
        low = href.lower()
        if "everywatch.com" in low and "/watch-" in low:
            return href.split("?", 1)[0]
    return None


def parse_watch_hits_from_html(html: str, *, page_url: str) -> list[dict[str, Any]]:
    """Parse listing cards: url, label, amount, currency (if found in anchor text)."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    hits: list[dict[str, Any]] = []
    for a in soup.select('a[href*="everywatch.com"]'):
        href = a.get("href")
        full = _abs_url(href or "")
        if not full or "/watch-" not in full:
            continue
        if full in seen:
            continue
        seen.add(full)
        label = " ".join((a.get_text() or "").split())
        if len(label) < 6:
            continue
        m = _PRICE_RE.search(label)
        amount: str | None = None
        currency: str | None = None
        if m:
            amount = m.group(1).replace(",", "")
            currency = m.group(2).upper()
        hits.append(
            {
                "url": full,
                "label": label[:500],
                "amount": amount,
                "currency": currency,
            }
        )
        if len(hits) >= 60:
            break
    return hits


def _median_amounts(hits: list[dict[str, Any]]) -> tuple[Decimal, str] | None:
    """Return (median, currency) using first currency seen (usually USD)."""
    amounts: list[tuple[Decimal, str]] = []
    for h in hits:
        raw_amt = h.get("amount")
        ccy = h.get("currency")
        if not raw_amt or not ccy:
            continue
        try:
            amounts.append((Decimal(str(raw_amt)), str(ccy).upper()))
        except InvalidOperation:
            continue
    if not amounts:
        return None
    currency = amounts[0][1]
    same = [a for a, c in amounts if c == currency]
    if len(same) < len(amounts) * 0.5:
        same = [a for a, _ in amounts]
        currency = amounts[0][1]
    same.sort()
    mid = same[len(same) // 2]
    return mid, currency


def fetch_everywatch_page(
    url: str,
    settings: Settings | None = None,
    timeout: float = 28.0,
) -> tuple[str | None, str | None]:
    """GET page HTML or (None, error)."""
    settings = settings or get_settings()
    ua = settings.watchbase_import_user_agent or _DEFAULT_UA
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            if r.status_code == 404:
                return None, "404"
            r.raise_for_status()
            return r.text, None
    except httpx.HTTPError as e:
        logger.warning("Everywatch fetch %s failed: %s", url, e)
        return None, str(e)
    except OSError as e:
        return None, str(e)


def collect_everywatch_snapshot(
    brand: str,
    reference: str | None,
    model_family: str | None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Try model URLs; return snapshot dict for JSONB (hits, median, errors).
    """
    settings = settings or get_settings()
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    urls = candidate_model_urls(brand, reference, model_family)
    if not urls:
        return {
            "fetched_at": now,
            "error": "Need brand and reference or model family for Everywatch URL.",
            "source_urls_tried": [],
            "hits": [],
        }

    last_err: str | None = None
    for url in urls:
        html, err = fetch_everywatch_page(url, settings=settings)
        if not html:
            last_err = err or "empty"
            continue
        hits = parse_watch_hits_from_html(html, page_url=url)
        if not hits:
            last_err = "no watch links parsed"
            continue
        med = _median_amounts(hits)
        snap: dict[str, Any] = {
            "fetched_at": now,
            "source_url": url,
            "source_urls_tried": urls,
            "hits": hits[:40],
            "error": None,
        }
        if med:
            snap["median_amount"] = str(med[0])
            snap["median_currency"] = med[1]
        return snap

    return {
        "fetched_at": now,
        "error": last_err or "failed",
        "source_urls_tried": urls,
        "hits": [],
    }
