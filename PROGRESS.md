# WatchFinder — implementation progress

Last updated: **10 April 2026**

This document records what is implemented in the repository versus the phased plan in **`Kickoff Documents/CURSOR_PROMPT.txt`**, plus later features (settings, valuation).

**Where to read what**

| Topic | Document |
|-------|----------|
| Run locally, Docker, CI, Unraid summary | Root **`README.md`** |
| Step-by-step Unraid (novice) | **`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`** |
| Unraid XML field list | **`deploy/unraid/watchfinder.xml`** (or your local template copy) |
| Environment variables | **`.env.example`** |
| Original full spec | **`Kickoff Documents/CURSOR_PROMPT.txt`** |

---

## Summary

| Phase | Scope | Status |
|-------|--------|--------|
| **1** | Backend skeleton, models, Alembic, config, eBay clients, ingestion, startup | **Done** |
| **2** | Parsing, repair keywords, scoring + explanations, API routes | **Done** |
| **3** | Next.js 14 UI (dashboard, listings, detail, candidates), Tailwind, shadcn-style components | **Done** |
| **4** | Dockerfile, `.env.example`, GitHub Actions, Unraid XML, README, compose | **Done** |
| **5** | Settings UI (multi-line ingest, interval, ingest-now); listing **valuation** edits, internal comps, **`listing_edits`** / **`watch_sale_records`**, migration **002** | **Done** |
| **5b** | **`watch_models`** catalog, **`listings.watch_model_id`**, auto-link + manual override, observed/manual price bounds, **`/watch-models`** UI, migration **003** | **Done** |
| **5c** | **`watch_model_link_reviews`** queue, **`watch_catalog_review_mode`**, **`/watch-review`**, migration **004** | **Done** |
| **5d** | Dashboard eBay counters, thumbnails, **`title_q`**, persisted search limit, shared Browse client per cycle, **`api_usage`** | **Done** |
| **6** | Multi-page ingest (**`ingest_max_pages`**), Browse **getItem** refresh + **`is_active=false`** on 404, wider **`ebay_item_id`**, migration **005**, pytest scaffold, **scheduled stale batch getItem** | **Done** |

---

## Phase 6 (complete)

- **Multi-page search ingest** (`job.py`): for each query line, up to **`ingest_max_pages`** calls to **`item_summary/search`** with `offset = page × limit`. Settings + **`app_settings.ingest_max_pages`**; env **`INGEST_MAX_PAGES`** default.
- **Live item** (`browse.py` **`get_item`**, `live_refresh.py`): **`POST /api/listings/{id}/refresh-from-ebay`**; increments **`browse_get_item`** usage counter; listing detail UI **Refresh from eBay**; **`404`** → **`is_active=false`**.
- **Stale batch refresh**: APScheduler job **`stale_listing_refresh`** (`services/stale_listing_refresh.py`, **`stale_refresh_worker.py`**) — active listings with **`last_seen_at`** older than configurable **min age** (or null; **0** = any past timestamp), up to **max per run**, **~0.35s** between **getItem** calls. One shared **`EbayBrowseClient`** + **`EbayAuthClient`** per batch (single OAuth token while cached). Toggle + limits in **Settings** (persisted **`app_settings`**); env **`STALE_LISTING_REFRESH_*`** defaults. **`POST /api/ingest/stale-refresh-run`** for a manual batch; logs explain **attempted: 0** when no rows match the age filter.
- **Listings / candidates API**: **`listing_active`** (**active** / **inactive** / **all**) and **`exclude_quartz`** query filters; UI status column and filters.
- **Schema** migrations **005**–**009**: **`ebay_item_id`** width **128**; **`watch_models`** spec columns + **`reference_url`**; **`external_price_history`** (JSONB) + **`watchbase_imported_at`**; **`008`** **`market_source_snapshots`** (Everywatch/Chrono24 JSON); **`009`** **`everywatch_url`** (optional exact Everywatch listing page for snapshots / **`GET /api/market/search`**).
- **Tests**: **`pytest`**, **`tests/test_mapper.py`**, **`tests/test_stale_listing_refresh.py`** (bool parsing), **`tests/test_everywatch_client.py`** (Everywatch URL helpers); **`requirements-dev.txt`**; **`ingestion` package `__init__`** no longer imports **`job`** at import time (avoids loading DB for mapper-only tests).
- **Watch catalog filtering**: **`GET /api/watch-models`** — **`pricing`** (`has_signal` / `missing_signal` / strict P3 gap), **`import_status`** (WatchBase unmatched vs matched), and excluded brands (**`WATCH_CATALOG_EXCLUDED_BRANDS`** env **merged** with **`watch_catalog_excluded_brands`** in **Settings** / **`app_settings`**). UI: **Price data** and **WatchBase** dropdowns on **`/watch-models/`**; batch presets call the same query params.
- **Everywatch debug**: **`POST /api/everywatch/debug`** + UI **`/watch-models/everywatch-test/`** (linked from model detail); optional **`cookie_header`** or saved **`everywatch_login_*`** in Settings (plaintext in **`app_settings`**) → API **`POST https://api.everywatch.com/api/Auth/Login`** for session headers; structured **`analysis`** JSON for import mapping experiments.

---

## Phase 1 (complete)

- **FastAPI** app in `backend/watchfinder/main.py` with lifespan, **`GET /health`**, and **APScheduler** running Browse ingest, optional stale-listing **getItem** sweep, and optional **match queue sync** (interval from DB **`app_settings`** or env).
- **Settings** via `pydantic-settings` (`watchfinder/config.py`): `DATABASE_URL`, eBay credentials, marketplace, search query/limit, **`ingest_max_pages`**, etc.
- **PostgreSQL** via SQLAlchemy 2 + **psycopg** (`watchfinder/db.py`).
- **Models** (`watchfinder/models/listing.py`): `listings`, `listing_snapshots`, `parsed_attributes`, `repair_signals`, `opportunity_scores`, `saved_searches`, `app_settings`, **`listing_edits`**, **`watch_sale_records`**, **`watch_models`** (listing **`watch_model_id`** FK **SET NULL**).
- **Alembic**: **001**–**008** (latest: **`market_source_snapshots`**; **007** WatchBase import columns; **006** specs + **`reference_url`**).
- **eBay**: client-credentials OAuth (`services/ebay/auth.py`), **Browse** search + **getItem** (`browse.py`), **Taxonomy** client stub (`taxonomy.py`).
- **Ingestion**: `mapper.py`, `job.py`, `live_refresh.py`; multi-query cycle from **`saved_searches`** or env fallback; shared **`EbayBrowseClient`** per cycle.
- **Docker** / **CI** / **Kickoff docs** as before.

---

## Phase 2 (complete)

- **Parsing**, **repair**, **scoring**, **pipeline**, **REST API** (includes **`POST .../refresh-from-ebay`**, dashboard **`ebay_browse_get_item_calls`**), **`api/query.py`** (**`title_q`**), **`listing_detail.py`**.
- **Repair opportunity scoring (2026):** **`analyze_listing`** links the watch catalog **before** scoring so **`watch_models`** £ bounds can anchor resale. **`services/scoring/catalog_anchor.py`** (manual midpoint/high/low, then observed), **`listing_gbp.py`** (Frankfurter **→ GBP**, process cache). **`engine.py`**: catalog path vs list×multiplier fallback; **parts** categories scale anchor ×0.55; confidence +0.08 when catalog anchor used. **`ListingSummary.watch_model_id`** for list APIs; candidates UI **Catalog** column.

OpenAPI: **`/docs`**.

---

## Phase 3 (complete)

- **Pages**: dashboard (extra counter card), listings, listing detail (**Refresh from eBay**, active/inactive badge), candidates, settings (**pages per search line**, **stale listing refresh**), watch-models, watch-review.
- **UI (2026):** **`money()`** in **`frontend/lib/format.ts`** formats with **Intl** currency (default **GBP** when code missing); **`currencyInputLabelSuffix`** for numeric field labels. Explanatory **CardDescription** / intro copy on listing detail, watch detail/list, listings/candidates tables (**SortableTableHead** `title`), dashboard, match queue, and **Settings** (**Prices & currencies**, **Save & manual jobs**). Watch detail: **Refresh data from WatchBase** (same as import).
- **Watch database / WatchBase / markets (2026):** **`GET /api/market/search`** aggregates WatchBase + **Everywatch** (HTML parse, price hints; optional **`everywatch_url`** query = saved **`watch_models.everywatch_url`** for exact **`/brand/watch-…`** pages before guessed listing URLs) + **Chrono24** (search/Google links; server fetch often **403**). **`market_source_snapshots`** on **`watch_models`**; auto refresh on **`analyze_listing`** and **backfill** when **`EXTRA_MARKET_IMPORT_ENABLED`** (cooldown **`MARKET_SNAPSHOT_COOLDOWN_HOURS`**); **`POST /api/watch-models/{id}/refresh-market-snapshots`** on a **watch detail** URL also fills **empty** **`spec_*` / `caliber` / `image_urls`** from parsed Everywatch HTML; seeds missing **manual £ low/high** from Everywatch **GBP** samples when available (detail **`price_analysis`** / hit amounts), else ±10% from median via Frankfurter if **both** manual bounds empty. UI: detail **Everywatch watch URL** field (WatchBase card), **Find on markets…** modal (passes URL to API), **Everywatch & Chrono24 snapshots** card; batch wizard shows EW/C24 alongside WatchBase.
- **Watch database / WatchBase (2026):** **`/watch-models/`** — **Search and filters**: **`q`** (OR on brand / reference / family / model name) plus **`brand`**, **`reference`**, **`model_family`**, **`model_name`**, **`caliber`** query params (contains, AND); same filters drive the table and catalog presets (**`appendWatchModelListFilters`**, **`fetchAllWatchModels`**). **Rows per page** UI: **25 / 50 / 100 / 200 / 500 / all** (all = full filtered list via **`fetchAllWatchModels`**); persisted **`watchfinder-watch-models-page-size`**. **Delete selected (N)** on the batch card: multi-row **`DELETE`** with confirm. Checkbox selection (Shift+range on current page), **Select all on page** / **none**, presets **Select unmatched (catalog)** (U3) and **Select without pricing (catalog)** (P3). **Supervised WatchBase import** draggable modeless wizard: side-by-side large images, auto + manual **`/api/market/search`** (WatchBase + Everywatch links + Chrono24 buttons), saved Reference URL, **Delete this catalog entry**, paste WatchBase URL, **No match — skip**; random **1–5 s** delay; **Open full detail** in new tab. Backend list filters **`watch_models.py`**. Helpers **`frontend/lib/watch-models-batch.ts`**, **`WatchbaseBatchWizard`**.

---

## Phase 4 (complete)

- **`Dockerfile`**: multi-stage Node + Python; **`HEALTHCHECK`**; non-root **`watchfinder`**.
- **`.env.example`**: backend settings documented.
- **`.github/workflows/docker-publish.yml`**: GHCR, Buildx, GHA cache.
- **`deploy/unraid/watchfinder.xml`**: template (paths, envs, **`watchfinder-net`**).
- **`docker-compose.yml`**: **postgres:16** + app **build**.

## Phase 5 — Settings & valuation (complete)

- **Persisted ingest**: **`saved_searches`** rows with `filter_json.kind === "browse_ingest"`; interval in **`app_settings.ingest_interval_minutes`**; **page size** in **`app_settings.ingest_search_limit`**; **`ingest_max_pages`** (Phase 6) in **`app_settings`**; **`services/ingest_settings.py`**, **`ingest_schedule.py`**, **`ingest_worker.py`**, **`runtime.py`** for scheduler reschedule.
- **Valuation** (`services/valuation/`): **effective** brand/model/ref/caliber (manual overrides vs parsed **R**); **`compute_comp_bands`** — sale records + active same-brand asking; **`sales_sync`** writes **`watch_sale_records`** when a **recorded sale** is saved; optional **`app_settings.max_comp_candidates`** (default **200** in code).
- **Provenance letters** (UI + API): **M / I / S / R / O / H / P** — see **`README.md` → Valuation**. **O** partially addressed by live **getItem** refresh (Phase 6); full “observed ended” automation still open.
- **Frontend**: Settings page fixes (**`newClientKey`** for HTTP LAN); listing detail form + guidance from **`field_guidance`**.

## Phase 5b — Watch database (complete)

- **Schema**: **`watch_models`** (brand, model family/name, reference, caliber, image URLs, production dates, description, **manual** and **observed** price low/high). Partial unique index: normalized **brand + reference** when reference is non-empty.
- **Matching + create + queue**: **`auto`** vs **`review`** mode; **`watch_model_link_reviews`**; **`POST /api/watch-link-reviews/{id}/resolve`**; **`promote-watch-catalog`** bypasses queue; listing detail **Catalogue review pending** banner.
- **Observed bounds**: linked listings + compatible **`watch_sale_records`**; refreshed on analyze and model changes.
- **API / UI**: **`/api/watch-models`**, nav **Watch database**, listing **Watch catalog link** card. **Watch model detail**: optional **spec** fields + **Reference URL**; **WatchBase** guess + Google links; **`POST …/import-watchbase`** fetches public HTML + **`/prices`** JSON (EUR list price history in **`external_price_history`**), **BeautifulSoup** table parse, **`WATCHBASE_IMPORT_ENABLED`**. **Dashboard** “Recently added” uses **`first_seen_at`**.
- **WatchBase import (extended):** info-table **Family** → **`model_family`**; when **`/prices`** parses, min/max EUR → **`manual_price_low` / `manual_price_high`** in **GBP** via [Frankfurter](https://www.frankfurter.app/) ECB rates, with optional env **`EUR_GBP_RATE_FALLBACK`** if the FX request fails. **`GET`/`PATCH`/`POST` watch-model responses** include **`linked_ebay_urls`** (distinct **`web_url`** from active listings linked to the model). Detail UI: **External links** card (clickable WatchBase + eBay URLs); **Find on WatchBase** modal uses the same **Photo size** control as listings / watch DB tables (persisted **`watchfinder-watchbase-find-thumb-size`**).

## Phase 5c — Match queue (complete)

- Migration **004**; **`/watch-review/`** UI; candidate scoring and settings **`watch_catalog_review_mode`**.
- **Match queue sync (2026):** APScheduler job **`match_queue_sync`** — re-runs **`analyze_listing`** on every **active** listing with **`watch_model_id` IS NULL** so the queue stays populated after ingest gaps or mode changes. Interval from **`app_settings.match_queue_sync_interval_minutes`** or env **`MATCH_QUEUE_SYNC_INTERVAL_MINUTES`** (**0** = disabled). **`POST /api/watch-link-reviews/sync-from-unmatched`** and the Match queue **Sync unmatched listings** button run the same pass. **`analyze_listing`** returns **`CatalogLinkOutcome`** for stats.

---

## Planned / not done yet

| Item | Notes |
|------|--------|
| **Observed sale (O)** | **Partial:** per-listing + batch **getItem** + inactive flag; still no “last sold price” persistence as first-class **O** source or dedicated ended-item pricing. |
| **AI / search hooks (I, S)** | UI sources exist; no OpenAI or external watch DB integration. |
| **Reference-tight sale comps** | Listing comp bands could weight **`watch_model`** link more heavily. |
| **Saved searches** (generic filters) | `saved_searches` used for ingest lines only. |
| **Taxonomy**-driven ingest | Client stub only. |
| **Tests** | **Started:** mapper + stale-refresh helpers; expand to API, refresh, ingest job with mocks. |
| **npm audit** / Next upgrades | Per your policy. |

---

## Repository map (quick reference)

| Path | Role |
|------|------|
| `frontend/` | Next.js UI (static export) |
| `backend/watchfinder/main.py` | Entry, scheduler, routers, static mount |
| `backend/watchfinder/api/` | Routes, **`listing_detail.py`**, **`listing_sort.py`**, **`market.py`**, **`everywatch_debug.py`** (**`/api/everywatch/debug`**), deps, query |
| `backend/watchfinder/services/ebay/` | OAuth, Browse (**search** + **getItem**), **`api_usage.py`** |
| `backend/watchfinder/services/ingestion/` | **`job.py`**, **`mapper.py`**, **`live_refresh.py`** |
| `backend/watchfinder/services/everywatch_client.py` | Everywatch model-page fetch + HTML hit/price parse |
| `backend/watchfinder/services/everywatch_login.py` | **`POST /api/Auth/Login`** (api.everywatch.com) → session headers |
| `backend/watchfinder/services/everywatch_credentials_settings.py` | Persist **`everywatch_login_*`** in **`app_settings`** |
| `backend/watchfinder/services/everywatch_debug.py` | Debug HTML analysis for import tester |
| `backend/watchfinder/services/chrono24_client.py` | Chrono24 search URL + optional fetch / **`__NEXT_DATA__`** parse |
| `backend/watchfinder/services/market_snapshots.py` | **`market_source_snapshots`** refresh; analyze/backfill hook |
| `backend/watchfinder/services/market_unified_search.py` | Aggregates WatchBase + Everywatch + Chrono24 for UI |
| `backend/watchfinder/services/watch_models/exclusions.py` | Parse **`WATCH_CATALOG_EXCLUDED_BRANDS`** for list + catalog skip |
| `backend/watchfinder/services/scoring/` | **`engine.py`**, **`catalog_anchor.py`** (watch DB £ anchor), **`listing_gbp.py`** (Frankfurter → GBP), **`constants.py`** |
| `backend/watchfinder/services/stale_listing_refresh.py` | Stale **getItem** batch + scheduler sync |
| `backend/watchfinder/stale_refresh_worker.py` | APScheduler job entry |
| `backend/watchfinder/services/ingest_settings.py` | Ingest queries, interval, **`ingest_search_limit`**, **`ingest_max_pages`** |
| `tests/` | **`pytest`** targets |
| `alembic/versions/` | **001**–**008** |
| `pytest.ini` | `pythonpath = backend` |

---

## How to continue

1. Expand **pytest** (refresh endpoint with mocked httpx, stale batch with test DB).
2. **Reference-tight** comp bands when **`watch_model_id`** is set.
3. Tune repair scoring (parts factor, margin) now that **`watch_models`** anchors resale when linked.
4. First-class **O** (ended / last sold) if you want beyond **getItem** + inactive.

For Unraid deployment, use **`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`**. After pull, run **`alembic upgrade head`** (through **008**).
