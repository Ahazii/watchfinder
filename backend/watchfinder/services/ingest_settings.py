"""Persisted ingest queries (SavedSearch) and interval (AppSetting)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from watchfinder.config import Settings
from watchfinder.models import AppSetting, SavedSearch

INGEST_KIND = "browse_ingest"


@dataclass
class IngestQueryRow:
    id: uuid.UUID
    label: str
    query: str
    enabled: bool


def _row_from_saved(s: SavedSearch) -> IngestQueryRow | None:
    fj = s.filter_json or {}
    if fj.get("kind") != INGEST_KIND:
        return None
    q = (fj.get("q") or "").strip()
    if not q:
        return None
    return IngestQueryRow(
        id=s.id,
        label=(s.name or "").strip() or "Untitled",
        query=q,
        enabled=bool(fj.get("enabled", True)),
    )


def list_ingest_queries(db: Session) -> list[IngestQueryRow]:
    stmt = (
        select(SavedSearch)
        .where(SavedSearch.filter_json.contains({"kind": INGEST_KIND}))
        .order_by(SavedSearch.created_at)
    )
    rows: list[IngestQueryRow] = []
    for s in db.scalars(stmt).all():
        r = _row_from_saved(s)
        if r:
            rows.append(r)
    return rows


def replace_ingest_queries(db: Session, items: list[tuple[str, str, bool]]) -> None:
    """Replace all browse_ingest rows. Each item: (label, query, enabled)."""
    db.execute(
        delete(SavedSearch).where(
            SavedSearch.filter_json.contains({"kind": INGEST_KIND})
        )
    )
    for label, query, enabled in items:
        q = query.strip()
        if not q:
            continue
        db.add(
            SavedSearch(
                name=label.strip() or q[:80],
                filter_json={
                    "kind": INGEST_KIND,
                    "q": q,
                    "enabled": enabled,
                },
            )
        )
    db.commit()


def resolve_ingest_query_strings(db: Session, settings: Settings) -> list[str]:
    """Enabled non-empty queries from DB; if none, fall back to env EBAY_SEARCH_QUERY."""
    out: list[str] = []
    for r in list_ingest_queries(db):
        if r.enabled and r.query:
            out.append(r.query)
    if not out:
        env_q = (settings.ebay_search_query or "").strip()
        if env_q:
            out.append(env_q)
    return out


def get_ingest_search_limit(db: Session, settings: Settings) -> int:
    """Max item summaries per Browse search call; persisted override or env default."""
    row = db.get(AppSetting, "ingest_search_limit")
    if row and row.value_text:
        try:
            v = int(row.value_text.strip())
            return max(1, min(200, v))
        except ValueError:
            pass
    return max(1, min(200, int(settings.ebay_search_limit)))


def set_ingest_search_limit(db: Session, n: int) -> None:
    v = max(1, min(200, int(n)))
    row = db.get(AppSetting, "ingest_search_limit")
    if row:
        row.value_text = str(v)
    else:
        db.add(AppSetting(key="ingest_search_limit", value_text=str(v)))
    db.commit()


def get_ingest_interval_minutes(db: Session, settings: Settings) -> int:
    row = db.get(AppSetting, "ingest_interval_minutes")
    if row and row.value_text:
        try:
            v = int(row.value_text.strip())
            return max(5, min(1440, v))
        except ValueError:
            pass
    return max(5, min(1440, settings.ingest_interval_minutes))


def set_ingest_interval_minutes(db: Session, minutes: int) -> None:
    v = max(5, min(1440, int(minutes)))
    row = db.get(AppSetting, "ingest_interval_minutes")
    if row:
        row.value_text = str(v)
    else:
        db.add(AppSetting(key="ingest_interval_minutes", value_text=str(v)))
    db.commit()
