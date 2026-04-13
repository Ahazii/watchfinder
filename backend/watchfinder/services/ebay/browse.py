"""eBay Buy Browse API — item summary search."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

from watchfinder.services.ebay.auth import EbayAuthClient

if TYPE_CHECKING:
    from watchfinder.config import Settings

logger = logging.getLogger(__name__)
_ENDED_MARKER = 'class="error-header-v2__title">We looked everywhere.</h1>'
_SOLD_MARKER_RE = re.compile(
    r'<div[^>]+class="[^"]*\bvim\b[^"]*\bd-top-panel-message\b[^"]*"[^>]*>.*?'
    r'<span[^>]*>\s*This listing sold on\b.*?</span>',
    re.IGNORECASE | re.DOTALL,
)


class EbayBrowseClient:
    def __init__(self, settings: Settings, auth: EbayAuthClient) -> None:
        self._settings = settings
        self._auth = auth

    def _base_url(self) -> str:
        if self._settings.ebay_environment.lower() == "sandbox":
            return "https://api.sandbox.ebay.com/buy/browse/v1"
        return "https://api.ebay.com/buy/browse/v1"

    def search(
        self,
        query: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        token = self._auth.get_application_token()
        params: dict[str, str | int] = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self._settings.ebay_marketplace_id,
        }
        url = f"{self._base_url()}/item_summary/search"
        with httpx.Client(timeout=60.0) as client:
            r = client.get(url, params=params, headers=headers)
            if r.status_code >= 400:
                logger.error("Browse search failed: %s %s", r.status_code, r.text[:500])
            r.raise_for_status()
            return r.json()

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Buy Browse GET /item/{item_id}. Returns JSON body, or None if 404 (ended / unavailable).
        item_id is URL-encoded (e.g. v1|123|0 → v1%7C123%7C0).
        """
        token = self._auth.get_application_token()
        enc = quote(item_id.strip(), safe="")
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self._settings.ebay_marketplace_id,
        }
        url = f"{self._base_url()}/item/{enc}"
        with httpx.Client(timeout=60.0) as client:
            r = client.get(url, headers=headers)
            if r.status_code == 404:
                return None
            if r.status_code >= 400:
                logger.error("Browse get_item failed: %s %s", r.status_code, r.text[:500])
            r.raise_for_status()
            return r.json()

    def page_has_not_found_marker(self, web_url: str | None) -> bool | None:
        """
        Return True when the eBay web page shows the ended-listing marker.
        Return False when page fetched and marker is absent.
        Return None when URL missing or fetch fails.
        """
        if not web_url or not web_url.strip():
            return None
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                r = client.get(web_url, headers=headers)
                if r.status_code >= 400:
                    return None
                html = r.text
                return (_ENDED_MARKER in html) or bool(_SOLD_MARKER_RE.search(html))
        except Exception:
            logger.debug("Could not check eBay page marker for %s", web_url, exc_info=True)
            return None
