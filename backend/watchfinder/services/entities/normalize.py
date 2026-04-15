"""Normalize free-text for dictionary keys (brand/caliber/reference)."""

from __future__ import annotations

import re


_ws_re = re.compile(r"\s+")


def normalize_entity_key(s: str | None) -> str:
    if not s or not str(s).strip():
        return ""
    t = str(s).strip().lower()
    t = _ws_re.sub(" ", t)
    return t
