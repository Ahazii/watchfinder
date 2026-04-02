"""Persisted counters for outbound eBay HTTP calls (ingest paths)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from watchfinder.models import AppSetting

logger = logging.getLogger(__name__)

_KEY = "ebay_api_usage_json"
_DEFAULT: dict[str, int] = {"browse_search": 0, "oauth_token": 0}


def _parse(raw: str | None) -> dict[str, int]:
    if not raw or not raw.strip():
        return dict(_DEFAULT)
    try:
        data: Any = json.loads(raw)
        if not isinstance(data, dict):
            return dict(_DEFAULT)
        out = dict(_DEFAULT)
        for k in _DEFAULT:
            v = data.get(k)
            if isinstance(v, int) and v >= 0:
                out[k] = v
        return out
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid %s JSON, resetting counters", _KEY)
        return dict(_DEFAULT)


def get_ebay_api_usage(db: Session) -> dict[str, int]:
    row = db.get(AppSetting, _KEY)
    return _parse(row.value_text if row else None)


def _save(db: Session, counts: dict[str, int]) -> None:
    payload = json.dumps(counts, separators=(",", ":"))
    row = db.get(AppSetting, _KEY)
    if row is None:
        db.add(AppSetting(key=_KEY, value_text=payload))
    else:
        row.value_text = payload
    # Same ingest request often increments oauth then browse; without flush the
    # second call's db.get() misses the pending INSERT and tries another add → PK clash.
    db.flush()


def increment_browse_search(db: Session, n: int = 1) -> None:
    if n <= 0:
        return
    c = get_ebay_api_usage(db)
    c["browse_search"] = c["browse_search"] + n
    _save(db, c)


def increment_oauth_token(db: Session, n: int = 1) -> None:
    if n <= 0:
        return
    c = get_ebay_api_usage(db)
    c["oauth_token"] = c["oauth_token"] + n
    _save(db, c)
