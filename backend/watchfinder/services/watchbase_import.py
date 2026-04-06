"""On-demand import from WatchBase public watch page + /prices JSON (manual button, low volume)."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import WatchModel
from watchfinder.services.watchbase_chart_json import parse_price_chart_json
from watchfinder.services.watchbase_movement import caliber_from_watchbase_watch_html
from watchfinder.services.watchbase_path import (
    canonical_watch_url,
    guessed_watch_path,
    path_from_watchbase_url,
)
from watchfinder.services.watch_models import refresh_watch_model_observed_bounds

logger = logging.getLogger(__name__)

DEFAULT_UA = "WatchFinder/1.0 (private catalog; occasional on-demand page fetch)"


class WatchBaseImportError(Exception):
    """User-facing import failure."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _mm_decimal(s: str | None) -> Decimal | None:
    if not s:
        return None
    m = re.search(r"([\d.]+)\s*mm", s, re.I)
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except InvalidOperation:
        return None


def _meters_decimal(s: str | None) -> Decimal | None:
    if not s:
        return None
    m = re.search(r"([\d.]+)\s*m\b", s, re.I)
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except InvalidOperation:
        return None


def _produced_year(s: str | None) -> date | None:
    if not s:
        return None
    m = re.search(r"(19|20)\d{2}", s)
    if not m:
        return None
    y = int(m.group(0))
    if 1900 <= y <= 2100:
        return date(y, 1, 1)
    return None


def _parse_description_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one("div.watch-description")
    if not block:
        return None
    text = block.get_text("\n", strip=True)
    return text or None


def _parse_og_image(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return str(meta["content"]).strip() or None
    return None


def _parse_info_rows(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, str] = {}
    for table in soup.select("table.info-table"):
        for tr in table.find_all("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if not th or not td:
                continue
            key = th.get_text(strip=True).rstrip(":").strip()
            val = " ".join(td.get_text().split())
            if key and val:
                out[key] = val
    return out


def resolve_watch_path(wm: WatchModel, reference_url_override: str | None = None) -> str:
    for candidate in (
        (reference_url_override or "").strip() or None,
        (wm.reference_url or "").strip() or None,
    ):
        if candidate:
            p = path_from_watchbase_url(candidate)
            if p:
                return p
    g = guessed_watch_path(wm.brand, wm.model_family or "", wm.reference or "")
    if g:
        return g
    raise WatchBaseImportError(
        "Set a watchbase.com **Reference URL**, or fill **brand**, **model family**, and **reference** "
        "so we can build the page path.",
    )


def import_watchbase_for_model(
    db: Session,
    model_id: UUID,
    settings: Settings | None = None,
    *,
    reference_url_override: str | None = None,
) -> dict[str, Any]:
    """
    Fetch watch HTML + /prices JSON, merge into model. Does not change brand / reference / model_family
    (identity keys). Sets **reference_url** to canonical WatchBase page.
    """
    settings = settings or get_settings()
    if not settings.watchbase_import_enabled:
        raise WatchBaseImportError(
            "WatchBase import is disabled (WATCHBASE_IMPORT_ENABLED=false).",
            status_code=403,
        )
    wm = db.get(WatchModel, model_id)
    if wm is None:
        raise WatchBaseImportError("Watch model not found", status_code=404)

    path = resolve_watch_path(wm, reference_url_override=reference_url_override)
    page_url = canonical_watch_url(path)
    prices_url = f"{page_url}/prices"

    ua = getattr(settings, "watchbase_import_user_agent", None) or DEFAULT_UA
    timeout = httpx.Timeout(25.0)
    headers = {"User-Agent": ua, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}

    updated: list[str] = []

    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        r_page = client.get(page_url)
        if r_page.status_code == 404:
            raise WatchBaseImportError(
                f"WatchBase returned 404 for {page_url}. Check the URL or slugs.",
                status_code=502,
            )
        r_page.raise_for_status()
        html = r_page.text

        r_prices = client.get(prices_url)
        if r_prices.status_code == 404:
            price_payload: dict[str, Any] | None = None
        else:
            r_prices.raise_for_status()
            try:
                price_payload = r_prices.json()
            except json.JSONDecodeError as e:
                raise WatchBaseImportError(
                    f"Invalid JSON from WatchBase prices URL: {e}",
                    status_code=502,
                ) from e

    rows = _parse_info_rows(html)
    desc = _parse_description_html(html)
    og = _parse_og_image(html)

    now = datetime.now(UTC)
    canonical = page_url

    wm.reference_url = canonical
    updated.append("reference_url")

    if desc:
        wm.description = desc
        updated.append("description")

    name = rows.get("Name")
    if name:
        wm.model_name = name
        updated.append("model_name")

    cal = caliber_from_watchbase_watch_html(html)
    if cal:
        wm.caliber = cal
        updated.append("caliber")

    py = _produced_year(rows.get("Produced"))
    if py:
        wm.production_start = py
        updated.append("production_start")

    if rows.get("Materials"):
        wm.spec_case_material = rows["Materials"]
        updated.append("spec_case_material")
    if rows.get("Bezel"):
        wm.spec_bezel = rows["Bezel"]
        updated.append("spec_bezel")
    if rows.get("Glass"):
        wm.spec_crystal = rows["Glass"]
        updated.append("spec_crystal")
    if rows.get("Back"):
        wm.spec_case_back = rows["Back"]
        updated.append("spec_case_back")

    d_mm = _mm_decimal(rows.get("Diameter"))
    if d_mm is not None:
        wm.spec_case_diameter_mm = d_mm
        updated.append("spec_case_diameter_mm")
    h_mm = _mm_decimal(rows.get("Height"))
    if h_mm is not None:
        wm.spec_case_height_mm = h_mm
        updated.append("spec_case_height_mm")
    lug = _mm_decimal(rows.get("Lug Width"))
    if lug is not None:
        wm.spec_lug_width_mm = lug
        updated.append("spec_lug_width_mm")

    wr = _meters_decimal(rows.get("W/R"))
    if wr is not None:
        wm.spec_water_resistance_m = wr
        updated.append("spec_water_resistance_m")

    if rows.get("Color"):
        wm.spec_dial_color = rows["Color"]
        updated.append("spec_dial_color")
    if rows.get("Material"):
        wm.spec_dial_material = rows["Material"]
        updated.append("spec_dial_material")

    idx = rows.get("Indexes")
    hands = rows.get("Hands")
    if idx or hands:
        parts = []
        if idx:
            parts.append(f"Indexes: {idx}")
        if hands:
            parts.append(f"Hands: {hands}")
        wm.spec_indexes_hands = "; ".join(parts)
        updated.append("spec_indexes_hands")

    if price_payload:
        hist = parse_price_chart_json(price_payload)
        hist["fetched_at"] = now.isoformat()
        wm.external_price_history = hist
        updated.append("external_price_history")

    if og and (not wm.image_urls or len(wm.image_urls) == 0):
        wm.image_urls = [og]
        updated.append("image_urls")

    wm.watchbase_imported_at = now
    updated.append("watchbase_imported_at")

    db.flush()
    refresh_watch_model_observed_bounds(db, wm.id)
    db.commit()
    db.refresh(wm)

    logger.info(
        "WatchBase import model_id=%s path=%s fields=%s price_points=%s",
        model_id,
        path,
        updated,
        len((wm.external_price_history or {}).get("points") or []),
    )

    return {
        "canonical_url": canonical,
        "prices_url": prices_url,
        "fields_updated": sorted(set(updated)),
        "price_points": len((wm.external_price_history or {}).get("points") or []),
    }
