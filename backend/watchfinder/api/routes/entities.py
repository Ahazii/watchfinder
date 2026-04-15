from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.models import Brand, Caliber, StockReference
from watchfinder.schemas.entities import (
    BrandListResponse,
    BrandOut,
    CaliberListResponse,
    CaliberOut,
    StockReferenceListResponse,
    StockReferenceOut,
)

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/brands", response_model=BrandListResponse)
def list_brands(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    q: str | None = Query(None, description="Substring match on display_name"),
) -> BrandListResponse:
    conds = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        conds.append(func.lower(Brand.display_name).like(needle))
    count_q = select(func.count()).select_from(Brand)
    if conds:
        count_q = count_q.where(*conds)
    total = int(db.scalar(count_q) or 0)
    stmt = select(Brand)
    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(Brand.display_name).offset(skip).limit(limit)
    rows = db.scalars(stmt).all()
    return BrandListResponse(
        items=[BrandOut.model_validate(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/calibers", response_model=CaliberListResponse)
def list_calibers(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    q: str | None = Query(None, description="Substring match on display_text"),
) -> CaliberListResponse:
    conds = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        conds.append(func.lower(Caliber.display_text).like(needle))
    count_q = select(func.count()).select_from(Caliber)
    if conds:
        count_q = count_q.where(*conds)
    total = int(db.scalar(count_q) or 0)
    stmt = select(Caliber)
    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(Caliber.display_text).offset(skip).limit(limit)
    rows = db.scalars(stmt).all()
    return CaliberListResponse(
        items=[CaliberOut.model_validate(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stock-references", response_model=StockReferenceListResponse)
def list_stock_references(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    brand_id: UUID | None = Query(None),
    q: str | None = Query(None, description="Substring match on ref_text"),
) -> StockReferenceListResponse:
    conds = []
    if brand_id is not None:
        conds.append(StockReference.brand_id == brand_id)
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        conds.append(func.lower(StockReference.ref_text).like(needle))
    count_q = select(func.count()).select_from(StockReference)
    if conds:
        count_q = count_q.where(*conds)
    total = int(db.scalar(count_q) or 0)
    stmt = select(StockReference)
    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(StockReference.ref_text).offset(skip).limit(limit)
    rows = db.scalars(stmt).all()
    return StockReferenceListResponse(
        items=[StockReferenceOut.model_validate(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )
