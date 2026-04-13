from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.models import NotInterestedListing
from watchfinder.schemas.not_interested import NotInterestedListResponse, NotInterestedOut
from watchfinder.services.not_interested import restore_not_interested_item

router = APIRouter(prefix="/not-interested", tags=["not-interested"])


@router.get("", response_model=NotInterestedListResponse)
def list_not_interested(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    active_only: bool = Query(True),
    q: str | None = Query(None),
) -> NotInterestedListResponse:
    stmt = select(NotInterestedListing)
    count_stmt = select(func.count()).select_from(NotInterestedListing)
    if active_only:
        stmt = stmt.where(NotInterestedListing.is_active.is_(True))
        count_stmt = count_stmt.where(NotInterestedListing.is_active.is_(True))
    if q and q.strip():
        s = f"%{q.strip()}%"
        stmt = stmt.where(
            NotInterestedListing.ebay_item_id.ilike(s)
            | NotInterestedListing.last_listing_title.ilike(s)
        )
        count_stmt = count_stmt.where(
            NotInterestedListing.ebay_item_id.ilike(s)
            | NotInterestedListing.last_listing_title.ilike(s)
        )
    total = int(db.scalar(count_stmt) or 0)
    rows = db.execute(
        stmt.order_by(NotInterestedListing.updated_at.desc()).offset(skip).limit(limit)
    ).scalars().all()
    return NotInterestedListResponse(
        items=[NotInterestedOut.model_validate(r) for r in rows],
        total=total,
    )


@router.post("/{row_id}/restore", response_model=NotInterestedOut)
def restore_not_interested(row_id: UUID, db: Session = Depends(get_db)) -> NotInterestedOut:
    row = restore_not_interested_item(db, row_id)
    db.commit()
    return NotInterestedOut.model_validate(row)


@router.delete("/{row_id}", response_model=dict)
def delete_not_interested_record(row_id: UUID, db: Session = Depends(get_db)) -> dict:
    row = db.get(NotInterestedListing, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not-interested record not found")
    db.delete(row)
    db.commit()
    return {"status": "ok"}
