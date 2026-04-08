from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, nulls_last, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.config import get_settings
from watchfinder.models import Listing, WatchModel
from watchfinder.schemas.watch_models import (
    BackfillWatchCatalogResponse,
    MarketSnapshotsRefreshResponse,
    WatchBaseImportRequest,
    WatchBaseImportResponse,
    WatchModelCreate,
    WatchModelListResponse,
    WatchModelOut,
    WatchModelPatch,
)
from watchfinder.services.market_snapshots import refresh_market_snapshots_for_model
from watchfinder.services.watch_models import backfill_watch_catalog, refresh_watch_model_observed_bounds
from watchfinder.services.watchbase_import import WatchBaseImportError, import_watchbase_for_model

router = APIRouter(prefix="/watch-models", tags=["watch-models"])


def _linked_ebay_urls_for_model(db: Session, model_id: UUID) -> list[str]:
    stmt = (
        select(Listing.web_url)
        .where(
            Listing.watch_model_id == model_id,
            Listing.is_active.is_(True),
            Listing.web_url.isnot(None),
        )
        .order_by(nulls_last(Listing.last_seen_at.desc()))
        .limit(50)
    )
    seen: set[str] = set()
    out: list[str] = []
    for u in db.scalars(stmt).all():
        s = (u or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _watch_model_out(db: Session, wm: WatchModel) -> WatchModelOut:
    out = WatchModelOut.model_validate(wm)
    ebay = _linked_ebay_urls_for_model(db, wm.id)
    return out.model_copy(update={"linked_ebay_urls": ebay})


@router.post(
    "/backfill-from-listings",
    response_model=BackfillWatchCatalogResponse,
    summary="Link or create watch_models from all active listings",
)
def backfill_from_listings(db: Session = Depends(get_db)) -> BackfillWatchCatalogResponse:
    stats = backfill_watch_catalog(db)
    db.commit()
    return BackfillWatchCatalogResponse(**stats)


def _apply_search(stmt, q: str | None):
    if not q or not q.strip():
        return stmt
    needle = f"%{q.strip().lower()}%"
    return stmt.where(
        func.lower(WatchModel.brand).like(needle)
        | func.lower(func.coalesce(WatchModel.reference, "")).like(needle)
        | func.lower(func.coalesce(WatchModel.model_family, "")).like(needle)
        | func.lower(func.coalesce(WatchModel.model_name, "")).like(needle)
    )


def _apply_field_contains(stmt, column, value: str | None):
    if not value or not str(value).strip():
        return stmt
    needle = f"%{str(value).strip().lower()}%"
    return stmt.where(func.lower(func.coalesce(column, "")).like(needle))


def _apply_watch_model_list_filters(
    stmt,
    q: str | None,
    brand: str | None,
    reference: str | None,
    model_family: str | None,
    model_name: str | None,
    caliber: str | None,
):
    stmt = _apply_field_contains(stmt, WatchModel.brand, brand)
    stmt = _apply_field_contains(stmt, WatchModel.reference, reference)
    stmt = _apply_field_contains(stmt, WatchModel.model_family, model_family)
    stmt = _apply_field_contains(stmt, WatchModel.model_name, model_name)
    stmt = _apply_field_contains(stmt, WatchModel.caliber, caliber)
    return _apply_search(stmt, q)


@router.get("", response_model=WatchModelListResponse)
def list_watch_models(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    q: str | None = None,
    brand: str | None = Query(None, description="Contains match (case-insensitive) on brand"),
    reference: str | None = Query(None, description="Contains match on reference"),
    model_family: str | None = Query(None, description="Contains match on model family"),
    model_name: str | None = Query(None, description="Contains match on model name"),
    caliber: str | None = Query(None, description="Contains match on caliber"),
) -> WatchModelListResponse:
    count_stmt = _apply_watch_model_list_filters(
        select(func.count()).select_from(WatchModel),
        q,
        brand,
        reference,
        model_family,
        model_name,
        caliber,
    )
    total = db.scalar(count_stmt) or 0

    list_stmt = _apply_watch_model_list_filters(
        select(WatchModel),
        q,
        brand,
        reference,
        model_family,
        model_name,
        caliber,
    )
    rows = db.scalars(
        list_stmt.order_by(WatchModel.brand, nulls_last(WatchModel.reference))
        .offset(skip)
        .limit(limit)
    ).all()
    return WatchModelListResponse(
        items=[WatchModelOut.model_validate(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{model_id}/import-watchbase",
    response_model=WatchBaseImportResponse,
    summary="Import WatchBase specs + EUR list price history (on-demand)",
)
def post_import_watchbase(
    model_id: UUID,
    db: Session = Depends(get_db),
    body: WatchBaseImportRequest = Body(default_factory=WatchBaseImportRequest),
) -> WatchBaseImportResponse:
    try:
        data = import_watchbase_for_model(
            db,
            model_id,
            get_settings(),
            reference_url_override=body.reference_url,
        )
    except WatchBaseImportError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    return WatchBaseImportResponse(**data)


@router.post(
    "/{model_id}/refresh-market-snapshots",
    response_model=MarketSnapshotsRefreshResponse,
    summary="Refresh Everywatch + Chrono24 snapshot JSON (optional manual £ seed)",
)
def post_refresh_market_snapshots(
    model_id: UUID,
    db: Session = Depends(get_db),
) -> MarketSnapshotsRefreshResponse:
    out = refresh_market_snapshots_for_model(
        db, model_id, get_settings(), force=True
    )
    if not out.get("ok") and out.get("error") == "model not found":
        db.rollback()
        raise HTTPException(status_code=404, detail="Watch model not found")
    if out.get("skipped") == "EXTRA_MARKET_IMPORT_ENABLED=false":
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail="Extra market import disabled (EXTRA_MARKET_IMPORT_ENABLED=false).",
        )
    if out.get("ok"):
        db.commit()
    else:
        db.rollback()
    return MarketSnapshotsRefreshResponse(
        ok=bool(out.get("ok")),
        skipped=out.get("skipped"),
        error=out.get("error"),
        everywatch_hits=int(out.get("everywatch_hits") or 0),
        chrono24_hits=int(out.get("chrono24_hits") or 0),
        merged_manual_bounds=bool(out.get("merged_manual_bounds")),
    )


@router.get("/{model_id}", response_model=WatchModelOut)
def get_watch_model(model_id: UUID, db: Session = Depends(get_db)) -> WatchModelOut:
    wm = db.get(WatchModel, model_id)
    if not wm:
        raise HTTPException(status_code=404, detail="Watch model not found")
    return _watch_model_out(db, wm)


@router.post("", response_model=WatchModelOut)
def create_watch_model(body: WatchModelCreate, db: Session = Depends(get_db)) -> WatchModelOut:
    wm = WatchModel(
        brand=body.brand.strip(),
        model_family=body.model_family,
        model_name=body.model_name,
        reference=(body.reference.strip() if body.reference else None) or None,
        caliber=body.caliber,
        image_urls=body.image_urls,
        production_start=body.production_start,
        production_end=body.production_end,
        description=body.description,
        manual_price_low=body.manual_price_low,
        manual_price_high=body.manual_price_high,
    )
    db.add(wm)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate brand+reference or constraint violation",
        ) from e
    refresh_watch_model_observed_bounds(db, wm.id)
    db.commit()
    db.refresh(wm)
    return _watch_model_out(db, wm)


@router.patch("/{model_id}", response_model=WatchModelOut)
def patch_watch_model(
    model_id: UUID, body: WatchModelPatch, db: Session = Depends(get_db)
) -> WatchModelOut:
    wm = db.get(WatchModel, model_id)
    if not wm:
        raise HTTPException(status_code=404, detail="Watch model not found")
    data = body.model_dump(exclude_unset=True)
    if "brand" in data and data["brand"] is not None:
        data["brand"] = data["brand"].strip()
    if "reference" in data:
        r = data["reference"]
        data["reference"] = (r.strip() if r else None) or None
    for k, v in data.items():
        setattr(wm, k, v)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate brand+reference or constraint violation",
        ) from e
    refresh_watch_model_observed_bounds(db, wm.id)
    db.commit()
    db.refresh(wm)
    return _watch_model_out(db, wm)


@router.delete("/{model_id}", status_code=204)
def delete_watch_model(model_id: UUID, db: Session = Depends(get_db)) -> None:
    wm = db.get(WatchModel, model_id)
    if not wm:
        raise HTTPException(status_code=404, detail="Watch model not found")
    db.delete(wm)
    db.commit()
