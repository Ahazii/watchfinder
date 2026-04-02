"""eBay application OAuth2 (client credentials) token."""

from __future__ import annotations

import base64
import logging
import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from watchfinder.config import Settings

logger = logging.getLogger(__name__)

# Client-credentials scopes — must match what your eBay app is allowed to use.
# If token requests fail with invalid_scope, add the Browse-specific scope from eBay docs.
_SCOPE_PROD = "https://api.ebay.com/oauth/api_scope"
_SCOPE_SANDBOX = "https://api.sandbox.ebay.com/oauth/api_scope"


class EbayAuthClient:
    def __init__(self, settings: Settings, db: "Session | None" = None) -> None:
        self._settings = settings
        self._db = db
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _token_url(self) -> str:
        if self._settings.ebay_environment.lower() == "sandbox":
            return "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
        return "https://api.ebay.com/identity/v1/oauth2/token"

    def _scope(self) -> str:
        if self._settings.ebay_environment.lower() == "sandbox":
            return _SCOPE_SANDBOX
        return _SCOPE_PROD

    def get_application_token(self) -> str:
        now = time.time()
        if self._token and now < self._expires_at - 60:
            return self._token

        pair = f"{self._settings.ebay_client_id}:{self._settings.ebay_client_secret}"
        basic = base64.b64encode(pair.encode()).decode()
        data = {
            "grant_type": "client_credentials",
            "scope": self._scope(),
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        }
        with httpx.Client(timeout=30.0) as client:
            r = client.post(self._token_url(), data=data, headers=headers)
            r.raise_for_status()
            body = r.json()

        self._token = body["access_token"]
        self._expires_at = now + int(body.get("expires_in", 7200))
        logger.info("Refreshed eBay application token")
        if self._db is not None:
            from watchfinder.services.ebay.api_usage import increment_oauth_token

            increment_oauth_token(self._db)
        return self._token
