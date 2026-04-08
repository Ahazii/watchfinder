"""Fetch Everywatch model listing pages and extract watch rows + prices (best-effort HTML parse)."""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote, urlparse

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

_EW_HOST = re.compile(r"^(?:www\.)?everywatch\.com$", re.I)


def normalize_everywatch_watch_url(raw: str | None) -> str | None:
    """
    Accept a full Everywatch watch detail URL (…/brand/watch-123).
    Returns canonical https URL without query string, or None if not a watch page URL.
    """
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip().split("?", 1)[0].strip()
    if not s.lower().startswith("http"):
        return None
    try:
        p = urlparse(s)
    except ValueError:
        return None
    if p.scheme not in ("http", "https") or not p.netloc:
        return None
    if not _EW_HOST.match(p.netloc.split("@")[-1]):
        return None
    path = (p.path or "").rstrip("/")
    if "/watch-" not in path.lower():
        return None
    return f"https://{p.netloc.split('@')[-1]}{path}"


def is_everywatch_watch_detail_url(url: str) -> bool:
    u = (url or "").split("?", 1)[0].rstrip("/")
    if not u.lower().startswith("http") or "everywatch.com" not in u.lower():
        return False
    return re.search(r"/watch-\d+$", u, re.I) is not None


def _ld_find_price_currency(obj: Any) -> tuple[str | None, str | None]:
    if isinstance(obj, dict):
        p = obj.get("price")
        c = obj.get("priceCurrency")
        if p is not None and c:
            return str(p).replace(",", ""), str(c).upper()
        offers = obj.get("offers")
        if isinstance(offers, dict):
            r = _ld_find_price_currency(offers)
            if r[0]:
                return r
        if isinstance(offers, list):
            for o in offers:
                r = _ld_find_price_currency(o)
                if r[0]:
                    return r
        g = obj.get("@graph")
        if isinstance(g, list):
            for item in g:
                r = _ld_find_price_currency(item)
                if r[0]:
                    return r
        for v in obj.values():
            if isinstance(v, (dict, list)):
                r = _ld_find_price_currency(v)
                if r[0]:
                    return r
    elif isinstance(obj, list):
        for item in obj:
            r = _ld_find_price_currency(item)
            if r[0]:
                return r
    return None, None


def parse_watch_detail_hit(html: str, *, page_url: str) -> dict[str, Any] | None:
    """Single listing row from a watch detail page (title + optional price from HTML / JSON-LD)."""
    soup = BeautifulSoup(html, "html.parser")
    base = page_url.split("?", 1)[0].rstrip("/")
    h1 = soup.find("h1")
    title_el = soup.find("title")
    title = (h1.get_text(" ", strip=True) if h1 else "") or (
        title_el.get_text(strip=True) if title_el else ""
    )
    label = (title[:500] if len(title) >= 3 else base) or base

    amount: str | None = None
    currency: str | None = None
    for s in soup.find_all("script", type=lambda t: bool(t and "ld+json" in str(t).lower())):
        raw = (s.string or s.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        a, c = _ld_find_price_currency(data)
        if a and c:
            amount, currency = a, c
            break

    if not amount:
        for blob in (title, soup.get_text(" ", strip=True)[:12000]):
            m = _PRICE_RE.search(blob)
            if m:
                amount = m.group(1).replace(",", "")
                currency = m.group(2).upper()
                break

    return {
        "url": base,
        "label": label[:500],
        "amount": amount,
        "currency": currency,
    }


def slugify_segment(s: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "-", (s or "").strip().lower()).strip("-")
    return t or "watch"


def reference_alnum(ref: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", (ref or "").strip())


def guess_site_search_urls(search_query: str) -> list[str]:
    """
    Candidate GET URLs to probe how Everywatch exposes search (site may change; for debugging).
    Home search input id is often ew-search-home — actual API may differ.
    """
    q = (search_query or "").strip()
    if not q:
        return []
    enc = quote(q, safe="")
    base = EVERYWATCH_ORIGIN.rstrip("/")
    return [
        f"{base}/search?q={enc}",
        f"{base}/search?query={enc}",
        f"{base}/for-sale?q={enc}",
        f"{base}/for-sale?search={enc}",
        f"{base}/?q={enc}",
        f"{base}/watch-search?q={enc}",
    ]


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
    extra_headers: dict[str, str] | None = None,
) -> tuple[str | None, str | None, int | None]:
    """GET page HTML or (None, error, status_code). status_code set when a response was received."""
    settings = settings or get_settings()
    ua = settings.watchbase_import_user_agent or _DEFAULT_UA
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    if extra_headers:
        headers.update({k: v for k, v in extra_headers.items() if v})
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            code = r.status_code
            if r.status_code == 404:
                return None, "404", code
            r.raise_for_status()
            return r.text, None, code
    except httpx.HTTPStatusError as e:
        c = e.response.status_code if e.response is not None else None
        return None, str(e), c
    except httpx.HTTPError as e:
        logger.warning("Everywatch fetch %s failed: %s", url, e)
        return None, str(e), None
    except OSError as e:
        return None, str(e), None


def collect_everywatch_snapshot(
    brand: str,
    reference: str | None,
    model_family: str | None,
    settings: Settings | None = None,
    *,
    everywatch_url: str | None = None,
) -> dict[str, Any]:
    """
    Try saved watch detail URL first (if valid), then guessed model listing URLs.
    Returns snapshot dict for JSONB (hits, median, errors).
    """
    settings = settings or get_settings()
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    urls: list[str] = []
    nu = normalize_everywatch_watch_url(everywatch_url)
    if nu:
        urls.append(nu)
    for u in candidate_model_urls(brand, reference, model_family):
        if u not in urls:
            urls.append(u)
    if not urls:
        return {
            "fetched_at": now,
            "error": "Need a saved Everywatch watch URL, or brand plus reference or model family.",
            "source_urls_tried": [],
            "hits": [],
        }

    last_err: str | None = None
    for url in urls:
        html, err, _code = fetch_everywatch_page(url, settings=settings)
        if not html:
            last_err = err or "empty"
            continue
        is_detail = is_everywatch_watch_detail_url(url)
        if is_detail:
            one = parse_watch_detail_hit(html, page_url=url)
            hits = [one] if one and one.get("url") else []
        else:
            hits = parse_watch_hits_from_html(html, page_url=url)
        if not hits:
            last_err = "detail page produced no row" if is_detail else "no watch links parsed"
            continue
        med = _median_amounts(hits)
        snap: dict[str, Any] = {
            "fetched_at": now,
            "source_url": url,
            "source_urls_tried": urls,
            "hits": hits[:40],
            "error": None,
            "page_kind": "watch_detail" if is_detail else "listing",
            "saved_watch_url_used": bool(nu and url == nu),
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
