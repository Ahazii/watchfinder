from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    norm_key: str


class CaliberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_text: str
    norm_key: str


class StockReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand_id: UUID
    ref_text: str
    norm_key: str
    watch_model_id: UUID | None = None


class BrandListResponse(BaseModel):
    items: list[BrandOut]
    total: int
    skip: int
    limit: int


class CaliberListResponse(BaseModel):
    items: list[CaliberOut]
    total: int
    skip: int
    limit: int


class StockReferenceListResponse(BaseModel):
    items: list[StockReferenceOut]
    total: int
    skip: int
    limit: int
