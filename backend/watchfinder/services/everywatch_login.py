"""Email/password login against Everywatch backend API (for debug / session cookies)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

EW_API_LOGIN = "https://api.everywatch.com/api/Auth/Login"
EW_ORIGIN = "https://everywatch.com"


def login_everywatch_api(
    user_name: str,
    password: str,
    *,
    timeout: float = 35.0,
) -> tuple[dict[str, str], dict[str, Any]]:
    """
    POST /api/Auth/Login with userName + password (same as the web app).

    Returns (headers_for_fetches, meta) where headers may include Cookie and/or Authorization.
    meta includes raw JSON (redacted) and error string if login failed.
    """
    meta: dict[str, Any] = {"ok": False, "message": None, "has_pss_cookie": False}
    headers_out: dict[str, str] = {}
    ua = "Mozilla/5.0 (compatible; WatchFinder/1.0; private catalog)"
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": ua,
                "Origin": EW_ORIGIN,
                "Accept": "application/json",
            },
        ) as client:
            r = client.post(
                EW_API_LOGIN,
                json={"userName": (user_name or "").strip(), "password": password or ""},
            )
            meta["http_status"] = r.status_code
            try:
                body = r.json()
            except Exception:
                meta["message"] = (r.text or "")[:500]
                return headers_out, meta

            meta["success_flag"] = body.get("success")
            meta["message"] = body.get("message")
            meta["response_keys"] = list(body.keys())

            if not body.get("success"):
                return headers_out, meta

            pss = body.get("pssCookie")
            if pss:
                meta["has_pss_cookie"] = True
                headers_out["Cookie"] = f".ASPXFORMSAUTH={pss}"

            data = body.get("data") if isinstance(body.get("data"), dict) else {}
            token = data.get("accessToken") or data.get("token")
            if token:
                headers_out["Authorization"] = f"Bearer {token}"

            jar_parts = [f"{k}={v}" for k, v in r.cookies.items()]
            if jar_parts:
                existing = headers_out.get("Cookie", "")
                merged = "; ".join(p for p in [existing, "; ".join(jar_parts)] if p)
                headers_out["Cookie"] = merged

            meta["ok"] = True
            meta["data_keys"] = list(data.keys()) if isinstance(data, dict) else []
            return headers_out, meta
    except httpx.HTTPError as e:
        logger.warning("Everywatch API login HTTP error: %s", e)
        meta["message"] = str(e)
        return headers_out, meta
