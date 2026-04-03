"""eBay Buy Browse API — item summary search."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

from watchfinder.services.ebay.auth import EbayAuthClient

if TYPE_CHECKING:
    from watchfinder.config import Settings

logger = logging.getLogger(__name__)


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
