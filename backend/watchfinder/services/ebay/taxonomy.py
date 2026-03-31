"""eBay Commerce Taxonomy API (category tree / aspects) — minimal wrapper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from watchfinder.services.ebay.auth import EbayAuthClient

if TYPE_CHECKING:
    from watchfinder.config import Settings

logger = logging.getLogger(__name__)


class EbayTaxonomyClient:
    def __init__(self, settings: Settings, auth: EbayAuthClient) -> None:
        self._settings = settings
        self._auth = auth

    def _base_url(self) -> str:
        if self._settings.ebay_environment.lower() == "sandbox":
            return "https://api.sandbox.ebay.com/commerce/taxonomy/v1"
        return "https://api.ebay.com/commerce/taxonomy/v1"

    def get_category_tree(self, category_tree_id: str) -> dict[str, Any]:
        """Fetch a marketplace category tree by ID (from eBay docs for your marketplace)."""
        token = self._auth.get_application_token()
        url = f"{self._base_url()}/category_tree/{category_tree_id}"
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=60.0) as client:
            r = client.get(url, headers=headers)
            if r.status_code >= 400:
                logger.warning("Taxonomy get_category_tree: %s %s", r.status_code, r.text[:300])
            r.raise_for_status()
            return r.json()
