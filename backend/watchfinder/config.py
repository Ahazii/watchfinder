from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        alias="DATABASE_URL",
        description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@host:5432/db",
    )
    ebay_client_id: str = Field(..., alias="EBAY_CLIENT_ID")
    ebay_client_secret: str = Field(..., alias="EBAY_CLIENT_SECRET")
    ebay_environment: str = Field(
        "production",
        alias="EBAY_ENVIRONMENT",
        description="production | sandbox",
    )
    tz: str = Field("UTC", alias="TZ")
    app_port: int = Field(8080, alias="APP_PORT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Ingestion defaults (tune later / move to DB settings)
    ebay_search_query: str = Field(
        "wristwatch",
        alias="EBAY_SEARCH_QUERY",
        description="Browse API search query for scheduled ingest",
    )
    ebay_search_limit: int = Field(50, alias="EBAY_SEARCH_LIMIT", ge=1, le=200)
    ingest_max_pages: int = Field(
        1,
        alias="INGEST_MAX_PAGES",
        ge=1,
        le=20,
        description="Max Browse search result pages per query line (offset pagination)",
    )
    ebay_marketplace_id: str = Field(
        "EBAY_GB",
        alias="EBAY_MARKETPLACE_ID",
        description="e.g. EBAY_GB, EBAY_US — must match developer key + listings region",
    )
    ebay_category_tree_id: str | None = Field(
        None,
        alias="EBAY_CATEGORY_TREE_ID",
        description="Optional taxonomy category tree id for get_category_tree calls",
    )
    ingest_interval_minutes: int = Field(
        30,
        alias="INGEST_INTERVAL_MINUTES",
        ge=5,
        le=1440,
        description="APScheduler interval for Browse ingest",
    )
    stale_listing_refresh_enabled: bool = Field(
        False,
        alias="STALE_LISTING_REFRESH_ENABLED",
        description="When true (or set in app_settings), scheduler runs batch getItem for stale listings",
    )
    stale_listing_refresh_interval_minutes: int = Field(
        360,
        alias="STALE_LISTING_REFRESH_INTERVAL_MINUTES",
        ge=15,
        le=1440,
        description="How often the stale-listing refresh job runs",
    )
    stale_listing_refresh_max_per_run: int = Field(
        20,
        alias="STALE_LISTING_REFRESH_MAX_PER_RUN",
        ge=1,
        le=100,
        description="Max Browse getItem calls per stale-refresh run",
    )
    stale_listing_refresh_min_age_hours: int = Field(
        12,
        alias="STALE_LISTING_REFRESH_MIN_AGE_HOURS",
        ge=0,
        le=720,
        description="Only refresh active listings with last_seen_at null or older than this many hours (0 = any past timestamp)",
    )
    watchbase_import_enabled: bool = Field(
        True,
        alias="WATCHBASE_IMPORT_ENABLED",
        description="Allow POST import from WatchBase (button on watch model detail)",
    )
    watchbase_import_user_agent: str | None = Field(
        None,
        alias="WATCHBASE_HTTP_USER_AGENT",
        description="Optional override User-Agent for WatchBase HTTP requests",
    )
    extra_market_import_enabled: bool = Field(
        True,
        alias="EXTRA_MARKET_IMPORT_ENABLED",
        description="When true, fetch Everywatch (and attempt Chrono24) market snapshots on analyze/backfill; "
        "respects per-model cooldown",
    )
    market_snapshot_cooldown_hours: int = Field(
        24,
        alias="MARKET_SNAPSHOT_COOLDOWN_HOURS",
        ge=1,
        le=168,
        description="Skip automatic market snapshot refresh if last fetch newer than this many hours",
    )
    local_media_root: str = Field(
        "./data/media",
        alias="LOCAL_MEDIA_ROOT",
        description="Writable directory for cached watch images from eBay listings; mount a volume in Docker",
    )
    media_download_enabled: bool = Field(
        True,
        alias="MEDIA_DOWNLOAD_ENABLED",
        description="When false, skip fetching listing gallery images into local_media_root",
    )
    media_download_user_agent: str | None = Field(
        None,
        alias="MEDIA_DOWNLOAD_USER_AGENT",
        description="Optional User-Agent for listing image downloads",
    )
    eur_gbp_rate_fallback: float | None = Field(
        None,
        alias="EUR_GBP_RATE_FALLBACK",
        description="Optional GBP-per-EUR rate if Frankfurter API is unreachable (e.g. 0.85)",
    )
    watch_catalog_excluded_brands: str | None = Field(
        None,
        alias="WATCH_CATALOG_EXCLUDED_BRANDS",
        description="Comma-separated brand names to hide from GET /watch-models and skip in catalog "
        "link/create/backfill (case-insensitive), e.g. Apple,Fitbit",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def database_url_for_psycopg(url: str) -> str:
    """psycopg.connect() expects postgresql:// not postgresql+psycopg://."""
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url.removeprefix("postgresql+psycopg://")
    return url
