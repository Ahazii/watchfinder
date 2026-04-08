from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.config import get_settings
from watchfinder.models import WatchModel
from watchfinder.schemas.everywatch_debug import EverywatchDebugRequest, EverywatchDebugResponse
from watchfinder.services.everywatch_client import (
    candidate_model_urls,
    collect_everywatch_snapshot,
    guess_site_search_urls,
)
from watchfinder.services.everywatch_credentials_settings import (
    get_everywatch_login_email,
    get_everywatch_login_password,
)
from watchfinder.services.everywatch_debug import run_everywatch_debug_fetches
from watchfinder.services.everywatch_login import login_everywatch_api

router = APIRouter(prefix="/everywatch", tags=["everywatch-debug"])


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        s = (u or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


@router.post("/debug", response_model=EverywatchDebugResponse)
def post_everywatch_debug(
    body: EverywatchDebugRequest,
    db: Session = Depends(get_db),
) -> EverywatchDebugResponse:
    """
    Developer tool: fetch Everywatch HTML and return structured parse hints.
    Does not write to the database. Optional Cookie header for logged-in HTML (session only).
    """
    settings = get_settings()
    brief: dict | None = None
    urls: list[str] = []
    snap: dict | None = None

    if body.watch_model_id is not None:
        wm = db.get(WatchModel, body.watch_model_id)
        if not wm:
            raise HTTPException(status_code=404, detail="Watch model not found")
        brief = {
            "id": str(wm.id),
            "brand": wm.brand,
            "reference": wm.reference,
            "model_family": wm.model_family,
            "model_name": wm.model_name,
        }
        urls.extend(
            candidate_model_urls(
                wm.brand or "",
                wm.reference,
                wm.model_family,
            )
        )
        q = " ".join(
            p
            for p in [
                (wm.brand or "").strip(),
                (wm.model_family or "").strip(),
                (wm.reference or "").strip(),
            ]
            if p
        )
        if q:
            urls.extend(guess_site_search_urls(q))
        snap = collect_everywatch_snapshot(
            (wm.brand or "").strip(),
            wm.reference,
            wm.model_family,
            settings=settings,
            everywatch_url=wm.everywatch_url,
        )

    for q in body.search_queries:
        urls.extend(guess_site_search_urls(q))

    for u in body.extra_urls:
        if (u or "").strip():
            urls.append(u.strip())

    urls = _dedupe_urls(urls)
    if not urls:
        raise HTTPException(
            status_code=400,
            detail="No URLs to fetch: pass watch_model_id, search_queries, or extra_urls",
        )

    login_meta: dict | None = None
    auth_headers: dict[str, str] | None = None
    ch = (body.cookie_header or "").strip()
    if ch:
        login_meta = {"skipped": "cookie_header provided"}
    else:
        email_o = (body.override_login_email or "").strip()
        email_s = get_everywatch_login_email(db) if body.use_saved_everywatch_login else ""
        email = email_o or email_s
        if body.override_login_password is not None:
            password = body.override_login_password
        elif body.use_saved_everywatch_login:
            password = get_everywatch_login_password(db)
        else:
            password = ""

        want_login = bool(
            email_o
            or body.override_login_password is not None
            or body.use_saved_everywatch_login
        )
        if want_login:
            if email and (password or "").strip():
                auth_headers, raw_meta = login_everywatch_api(email, password)
                login_meta = {
                    "ok": raw_meta.get("ok"),
                    "http_status": raw_meta.get("http_status"),
                    "message": raw_meta.get("message"),
                    "has_pss_cookie": raw_meta.get("has_pss_cookie"),
                    "data_keys": raw_meta.get("data_keys"),
                    "response_keys": raw_meta.get("response_keys"),
                    "used_override_email": bool(email_o),
                }
            elif not email:
                login_meta = {"skipped": "missing email (Settings or override)"}
            else:
                login_meta = {"skipped": "missing password (Settings or override)"}
        else:
            login_meta = {"skipped": "saved login off and no overrides"}

    fetches = run_everywatch_debug_fetches(
        urls,
        settings=settings,
        cookie_header=body.cookie_header,
        auth_headers=auth_headers,
    )

    return EverywatchDebugResponse(
        watch_model_brief=brief,
        urls_attempted=urls,
        collect_everywatch_snapshot=snap,
        fetches=fetches,
        login_attempt=login_meta,
    )
