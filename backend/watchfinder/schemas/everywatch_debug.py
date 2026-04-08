from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EverywatchDebugRequest(BaseModel):
    watch_model_id: UUID | None = Field(
        None, description="Load brand/reference/family to build default URLs + snapshot"
    )
    extra_urls: list[str] = Field(
        default_factory=list,
        max_length=24,
        description="Additional absolute URLs to fetch (Everywatch pages)",
    )
    search_queries: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="Extra guessed search URLs per query string",
    )
    cookie_header: str | None = Field(
        None,
        max_length=8000,
        description="If set, used as Cookie header and skips API login for this request",
    )
    use_saved_everywatch_login: bool = Field(
        True,
        description="When true (and no cookie_header), use email/password from Settings (app_settings)",
    )
    override_login_email: str | None = Field(
        None,
        max_length=320,
        description="One-shot email for this debug request (does not persist)",
    )
    override_login_password: str | None = Field(
        None,
        max_length=2000,
        description="One-shot password for this debug request (does not persist)",
    )


class EverywatchDebugResponse(BaseModel):
    watch_model_brief: dict[str, Any] | None = None
    urls_attempted: list[str]
    collect_everywatch_snapshot: dict[str, Any] | None = None
    fetches: list[dict[str, Any]]
    login_attempt: dict[str, Any] | None = Field(
        None,
        description="Outcome of API login (no secrets); omitted if cookie_header was used",
    )
