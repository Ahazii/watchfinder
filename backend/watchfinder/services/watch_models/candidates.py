"""Rank watch_models as match candidates for a listing (same brand, scored)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchfinder.models import WatchModel
from watchfinder.services.valuation.effective import norm_key


def _score_candidate(
    wm: WatchModel,
    *,
    ref_listing: str | None,
    mf_listing: str | None,
    title_lower: str,
) -> float:
    s = 0.0
    rk_l = norm_key(ref_listing)
    rk_w = norm_key(wm.reference) if wm.reference else None
    if rk_l and rk_w:
        if rk_l == rk_w:
            s += 1.0
        elif rk_l in rk_w or rk_w in rk_l:
            s += 0.62
    mfk_l = norm_key(mf_listing)
    mfk_w = norm_key(wm.model_family) if wm.model_family else None
    if mfk_l and mfk_w and mfk_l == mfk_w:
        s += 0.58
    if wm.model_name and len((wm.model_name or "").strip()) >= 4:
        mn = (wm.model_name or "").strip().lower()
        if mn and mn in title_lower:
            s += 0.42
    return min(s, 1.0)


def rank_watch_model_candidates(
    db: Session,
    *,
    brand: str,
    reference: str | None,
    model_family: str | None,
    title: str | None,
    limit: int = 12,
) -> list[tuple[WatchModel, float]]:
    bk = norm_key(brand)
    if not bk:
        return []
    stmt = select(WatchModel).where(func.lower(func.trim(WatchModel.brand)) == bk)
    rows = list(db.scalars(stmt).all())
    title_l = (title or "").lower()
    ref_l = (reference or "").strip() or None
    mf_l = (model_family or "").strip() or None
    scored: list[tuple[WatchModel, float]] = []
    for wm in rows:
        sc = _score_candidate(wm, ref_listing=ref_l, mf_listing=mf_l, title_lower=title_l)
        if sc > 0:
            scored.append((wm, sc))
    scored.sort(key=lambda x: (-x[1], str(x[0].id)))
    return scored[:limit]
