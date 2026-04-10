"""Fetch Everywatch model listing pages and extract watch rows + prices (best-effort HTML parse)."""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from watchfinder.config import Settings, get_settings

logger = logging.getLogger(__name__)

EVERYWATCH_ORIGIN = "https://everywatch.com"
_DEFAULT_UA = "WatchFinder/1.0 (private catalog; occasional on-demand page fetch)"

_PRICE_RE = re.compile(
    r"([\d][\d,]*(?:\.\d+)?)\s*(USD|EUR|GBP)\b",
    re.IGNORECASE,
)
# Detail page "price analysis" block (often GBP).
_GBP_BLOCK_RE = re.compile(
    r"([\d][\d.,]*)\s*K\s*GBP|([\d][\d,]*(?:\.\d+)?)\s*GBP\b",
    re.IGNORECASE,
)

_EW_HOST = re.compile(r"^(?:www\.)?everywatch\.com$", re.I)


def _plain_text_from_maybe_html(s: str) -> str:
    """Strip tags / decode entities when anchors accidentally include HTML fragments."""
    if not s:
        return ""
    t = re.sub(r"<[^>]+>", " ", s)
    t = html_lib.unescape(t)
    return " ".join(t.split())


def _image_near_anchor(a: Tag) -> str | None:
    """Best-effort hero thumb for a watch card link."""
    for img in a.find_all("img", src=True, limit=12):
        src = (img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        return src.split(" ", 1)[0]
    el = a.parent
    for _ in range(8):
        if el is None or not isinstance(el, Tag):
            break
        img = el.find("img", src=True)
        if img:
            src = (img.get("src") or "").strip()
            if src and not src.startswith("data:"):
                return src.split(" ", 1)[0]
        el = el.parent
    return None


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


def _parse_gbp_tokens_from_text(text: str) -> list[tuple[str, str]]:
    """Return [(amount_str, 'GBP'), ...] from snippets like '547 GBP' or '1.48K GBP'."""
    out: list[tuple[str, str]] = []
    for m in _GBP_BLOCK_RE.finditer(text or ""):
        k_part, plain_part = m.group(1), m.group(2)
        if k_part:
            try:
                v = Decimal(k_part.replace(",", "")) * 1000
                out.append((str(v.quantize(Decimal("0.01"))), "GBP"))
            except InvalidOperation:
                pass
        elif plain_part:
            try:
                v = Decimal(plain_part.replace(",", ""))
                out.append((str(v), "GBP"))
            except InvalidOperation:
                pass
    return out


def parse_awd_spec_map(html: str) -> dict[str, str]:
    """Everywatch watch detail: li.awd-desc-items with .awd-title / .awd-detail."""
    soup = BeautifulSoup(html, "html.parser")
    specs: dict[str, str] = {}
    for li in soup.select("li.awd-desc-items"):
        t_el = li.select_one(".awd-title")
        d_el = li.select_one(".awd-detail")
        if not t_el or not d_el:
            continue
        key = t_el.get_text(" ", strip=True).rstrip(": ").strip()
        val = d_el.get_text(" ", strip=True)
        if key and val and key not in specs:
            specs[key] = val[:500]
    return specs


def parse_price_container_rows(html: str) -> list[dict[str, Any]]:
    """Everywatch detail: .price-container h3.price-analysis-item (Auction / Dealers / Range)."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".price-container")
    if not root:
        return []
    rows: list[dict[str, Any]] = []
    for h3 in root.select("h3.price-analysis-item"):
        title_el = h3.select_one(".p-title")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        price_el = h3.select_one(".price")
        raw_text = price_el.get_text(" ", strip=True) if price_el else ""
        gbp = _parse_gbp_tokens_from_text(raw_text)
        rows.append(
            {
                "title": title[:120],
                "raw_text": raw_text[:400],
                "gbp_amounts": [a for a, _ in gbp],
            }
        )
    return rows


def parse_detail_hero_image_url(html: str) -> str | None:
    """Prefer img.everywatch.com with eager / high priority, else first cdn image."""
    soup = BeautifulSoup(html, "html.parser")
    best: str | None = None
    for img in soup.find_all("img", src=True):
        src = (img.get("src") or "").strip()
        if "img.everywatch.com" not in src.lower():
            continue
        loading = (img.get("loading") or "").lower()
        fetch_pri = (img.get("fetchpriority") or "").lower()
        if loading == "eager" or fetch_pri == "high":
            return src.split(" ", 1)[0]
        if best is None:
            best = src.split(" ", 1)[0]
    return best


def parse_watch_detail_hit(html: str, *, page_url: str) -> dict[str, Any] | None:
    """Single listing row from a watch detail page (title + specs + image + prices)."""
    soup = BeautifulSoup(html, "html.parser")
    base = page_url.split("?", 1)[0].rstrip("/")
    h1 = soup.find("h1")
    title_el = soup.find("title")
    title = (h1.get_text(" ", strip=True) if h1 else "") or (
        title_el.get_text(strip=True) if title_el else ""
    )
    title = _plain_text_from_maybe_html(title)
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

    price_rows = parse_price_container_rows(html)
    if not amount and price_rows:
        for row in price_rows:
            amts = row.get("gbp_amounts") or []
            if amts:
                amount, currency = amts[0], "GBP"
                break

    specs = parse_awd_spec_map(html)
    image_url = parse_detail_hero_image_url(html)

    return {
        "url": base,
        "label": label[:500],
        "amount": amount,
        "currency": currency,
        "specs": specs,
        "image_url": image_url,
        "price_analysis": price_rows[:12],
    }


def slugify_segment(s: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "-", (s or "").strip().lower()).strip("-")
    return t or "watch"


def reference_alnum(ref: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", (ref or "").strip())


def guess_watch_listing_urls(search_query: str) -> list[str]:
    """
    Real Everywatch search results live under /watch-listing?query=… (see everywatch.com UI).
    Optional keyword= mirrors their filter when the last token looks like a reference (e.g. 166085).
    """
    q = (search_query or "").strip()
    if not q:
        return []
    enc = quote(q, safe="")
    base = EVERYWATCH_ORIGIN.rstrip("/")
    out: list[str] = [
        f"{base}/watch-listing?query={enc}&sortColumn=relevance&sortType=asc",
    ]
    parts = q.split()
    if parts:
        tail = reference_alnum(parts[-1])
        if tail and any(ch.isdigit() for ch in tail) and len(tail) >= 4:
            out.append(
                f"{base}/watch-listing?keyword={quote(tail, safe='')}&query={enc}"
                "&sortColumn=relevance&sortType=asc"
            )
    return out


def guess_site_search_urls(search_query: str) -> list[str]:
    """
    Prefer /watch-listing (works server-side); keep legacy paths as low-priority probes for debug.
    """
    q = (search_query or "").strip()
    if not q:
        return []
    enc = quote(q, safe="")
    base = EVERYWATCH_ORIGIN.rstrip("/")
    primary = guess_watch_listing_urls(q)
    legacy = [
        f"{base}/search?q={enc}",
        f"{base}/search?query={enc}",
        f"{base}/for-sale?q={enc}",
        f"{base}/for-sale?search={enc}",
        f"{base}/?q={enc}",
        f"{base}/watch-search?q={enc}",
    ]
    seen = set(primary)
    out = list(primary)
    for u in legacy:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


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
    """Parse listing cards: relative or absolute links to …/watch-<id> (e.g. /omega/de-ville/watch-1)."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    hits: list[dict[str, Any]] = []
    for a in soup.select('a[href*="watch-"]'):
        href = (a.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        full = _abs_url(href)
        if not full or "/watch-" not in full.lower():
            continue
        if full in seen:
            continue
        seen.add(full)
        label = _plain_text_from_maybe_html(" ".join((a.get_text() or "").split()))
        if len(label) < 4:
            label = _plain_text_from_maybe_html(
                (a.get("title") or "").strip()
            ) or full.rsplit("/watch-", 1)[-1]
        if len(label) < 3:
            continue
        m = _PRICE_RE.search(label)
        amount: str | None = None
        currency: str | None = None
        if m:
            amount = m.group(1).replace(",", "")
            currency = m.group(2).upper()
        img_url = _image_near_anchor(a)
        hits.append(
            {
                "url": full,
                "label": label[:500],
                "amount": amount,
                "currency": currency,
                "image_url": img_url,
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
    q_model = " ".join(
        p
        for p in [
            (brand or "").strip(),
            ((reference or "") or "").strip(),
            ((model_family or "") or "").strip(),
        ]
        if p
    )
    for u in guess_watch_listing_urls(q_model):
        if u not in urls:
            urls.append(u)
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
