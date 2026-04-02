# WatchFinder — implementation progress

Last updated: **3 April 2026**

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
| **5b** | **`watch_models`** catalog, **`listings.watch_model_id`**, auto-link + manual override, observed/manual price bounds, **`/watch-models`** UI, migration **003**, Settings copy for Browse `q` behavior | **Done** |
| **5c** | **`watch_model_link_reviews`** queue, **`watch_catalog_review_mode`** (`auto` / `review`), candidate scoring, **`/watch-review`** UI, **`/api/watch-link-reviews`**, migration **004** | **Done** |
| **5d** | Dashboard **eBay API counters** + doc links; **`image_urls`** on **`ListingSummary`** + thumbs (listings, candidates, watch DB, dashboard); **`title_q`** filter; **`app_settings.ingest_search_limit`** + Settings UI; **reuse one Browse client per ingest cycle** (OAuth not per line); **`services/ebay/api_usage.py`** (usage JSON + flush-safe saves) | **Done** |

---

## Phase 1 (complete)

- **FastAPI** app in `backend/watchfinder/main.py` with lifespan, **`GET /health`**, and **APScheduler** running Browse ingest (interval from DB **`app_settings`** or env).
- **Settings** via `pydantic-settings` (`watchfinder/config.py`): `DATABASE_URL`, eBay credentials, marketplace, search query/limit, etc.
- **PostgreSQL** via SQLAlchemy 2 + **psycopg** (`watchfinder/db.py`).
- **Models** (`watchfinder/models/listing.py`): `listings`, `listing_snapshots`, `parsed_attributes`, `repair_signals`, `opportunity_scores`, `saved_searches`, `app_settings`, **`listing_edits`**, **`watch_sale_records`**, **`watch_models`** (listing **`watch_model_id`** FK **SET NULL**).
- **Alembic**: `001_initial_schema.py`, **`002_listing_edits_watch_sales.py`**, **`003_watch_models.py`** (`watch_models`, `listings.watch_model_id`, partial unique index on brand + reference when reference is set).
- **eBay**: client-credentials OAuth (`services/ebay/auth.py`), **Browse** item summary search (`browse.py`), **Taxonomy** client stub (`taxonomy.py`).
- **Ingestion**: map item summaries → listing rows + snapshots (`services/ingestion/mapper.py`, `job.py`); multi-query cycle from **`saved_searches`** (`browse_ingest` JSON) or env fallback; **`run_all_browse_ingest`** shares one **`EbayBrowseClient`** (token reused across lines); per-search **`limit`** from **`get_ingest_search_limit`** (**`app_settings.ingest_search_limit`** or env).
- **Docker**: `docker/start.sh` (wait for Postgres, **`alembic upgrade head`**, `uvicorn`).
- **CI**: `.github/workflows/docker-publish.yml` → **GHCR** `ghcr.io/<repo_owner>/watchfinder`.
- **Kickoff docs**: `Kickoff Documents/` (novice Unraid runbook + Cursor prompt).

---

## Phase 2 (complete)

- **Parsing** (`services/parsing/`): corpus assembly; rules-first **brand / reference / movement / caliber / running_state**; tunable **repair phrase** list in `keywords.py`.
- **Repair signals** (`services/repair/extract.py`): non-overlapping phrase matches → stored `repair_signals` rows.
- **Scoring** (`services/scoring/`): rule-based resale/repair/margin math, **confidence**, **risk**, **explanations**; tunable numbers in `constants.py`. **Repair total** = rule core + optional **repair add-on** + **donor cost** from **`listing_edits`** (see Phase 5).
- **Pipeline** (`services/pipeline/analyze.py`): after each listing upsert (or PATCH), clears and repopulates parsed attributes, signals, and **at most one** current opportunity score row per listing (when repair signals exist). Then **`ensure_watch_catalog_for_listing`** (respects **`watch_catalog_review_mode`**) and **`refresh_watch_model_observed_bounds`** when linked (`services/watch_models/`).
- **REST API** (prefix `/api`):
  - `GET /api/dashboard` — includes **`ebay_browse_search_calls`** / **`ebay_oauth_token_calls`** and recent rows with **`image_urls`**
  - `GET /api/listings` (+ query filters including **`title_q`**, **`sort_by` / `sort_dir`**)
  - `GET /api/listings/{uuid}` — detail + comps + **`field_guidance`** / **`source_legend`**
  - **`PATCH /api/listings/{uuid}`** — persist **`listing_edits`**, optional **`watch_model_id`**, sync **`watch_sale_records`**, re-analyze (refresh prior model bounds if link changed)
  - **`GET` / `POST` / `GET/{uuid}` / `PATCH` / `DELETE` `/api/watch-models`** — watch catalog CRUD + search; **`POST /backfill-from-listings`**
  - **`POST /api/listings/{uuid}/promote-watch-catalog`** — force catalog link/create (bypasses review queue)
  - **`/api/watch-link-reviews`**: `GET` list, `GET /{uuid}` detail, `POST /{uuid}/resolve` — match queue (review mode)
  - `GET /api/candidates` (profit > 0, same sort params as listings)
  - **`GET` / `PATCH /api/settings`** (includes **`watch_catalog_review_mode`**), **`POST /api/ingest/run`**
- **Query layer** (`api/query.py`, `listing_helpers.py`) avoids duplicate rows from joins by using `EXISTS` subqueries; optional **`title_q`** filters **`Listing.title`** (ILIKE).
- **Listing detail assembly** (`api/listing_detail.py`).

OpenAPI: **`/docs`** (FastAPI) when the app is running.

---

## Phase 3 (complete)

- **`frontend/`** — Next.js 14 **App Router**, **TypeScript**, **Tailwind**, **shadcn-style** primitives, **DM Sans**, dark theme.
- **Static export** → `frontend/out/`; **FastAPI** mounts at **`/`** when present (after `/api`, `/health`, `/docs`).
- **Pages**:
  - **`/`** — Dashboard (eBay usage counters + policy links, recent listing thumbs).
  - **`/listings/`** — Filterable table (**Title contains**, brand, etc.), pagination, sortable columns, thumbnails, **Add to watch database** per row.
  - **`/listings/detail/?id=`** — eBay link, **internal comps**, **editable valuation form** (save → PATCH), score, explanations, signals, parsed attrs, source legend.
  - **`/candidates/`** — Profit-positive subset (**title_q** + shared filters with listings).
  - **`/settings/`** — Ingest lines, **interval** + **items per search line**, **Ingest now**; **watch catalog matching** (`auto` / `review`); Browse **`q`** + throughput help.
  - **`/watch-models/`**, **`/watch-models/detail/?id=`** — Watch database + **backfill from listings**.
  - **`/watch-review/`**, **`/watch-review/detail/?id=`** — Match queue (resolve link / create / dismiss).
  - **Listings / Candidates** — column headers sort server-side (`sort_by` / `sort_dir` on **`GET /api/listings`** and **`GET /api/candidates`**).
- **CORS** `allow_origins=["*"]`.
- **Local UI dev**: `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080` + API on **8080**.

---

## Phase 4 (complete)

- **`Dockerfile`**: multi-stage Node + Python; **`HEALTHCHECK`**; non-root **`watchfinder`**.
- **`.env.example`**: backend settings documented.
- **`.github/workflows/docker-publish.yml`**: GHCR, Buildx, GHA cache.
- **`deploy/unraid/watchfinder.xml`**: template (paths, envs, **`watchfinder-net`**).
- **`docker-compose.yml`**: **postgres:16** + app **build**.

---

## Phase 5 — Settings & valuation (complete)

- **Persisted ingest**: **`saved_searches`** rows with `filter_json.kind === "browse_ingest"`; interval in **`app_settings.ingest_interval_minutes`**; **page size** in **`app_settings.ingest_search_limit`** (override for **`EBAY_SEARCH_LIMIT`**); **`services/ingest_settings.py`**, **`ingest_schedule.py`**, **`ingest_worker.py`**, **`runtime.py`** for scheduler reschedule.
- **Valuation** (`services/valuation/`): **effective** brand/model/ref/caliber (manual overrides vs parsed **R**); **`compute_comp_bands`** — sale records + active same-brand asking; **`sales_sync`** writes **`watch_sale_records`** when a **recorded sale** is saved; optional **`app_settings.max_comp_candidates`** (default **200** in code).
- **Provenance letters** (UI + API): **M / I / S / R / O / H / P** — see **`README.md` → Valuation**. **O** reserved for future ingest-observed auction end (not implemented yet).
- **Frontend**: Settings page fixes (**`newClientKey`** for HTTP LAN); listing detail form + guidance from **`field_guidance`**.

---

## Phase 5b — Watch database (complete)

- **Schema**: **`watch_models`** (brand, model family/name, reference, caliber, image URLs, production dates, description, **manual** and **observed** price low/high). Partial unique index: normalized **brand + reference** when reference is non-empty.
- **Matching + create + queue**: **`auto`** mode: same as before — exact + fuzzy + create. **`review`** mode ( **`app_settings.watch_catalog_review_mode`** ): **exact** match only on analyze; if still unlinked with **brand + (ref or family)**, upsert **`watch_model_link_reviews`** with **ranked candidate** model ids + scores + tier (`high` / `medium` / `low`). **`POST /api/watch-link-reviews/{id}/resolve`** → match / create / dismiss. **`promote-watch-catalog`** always **bypasses** the queue. Listing detail shows **Catalogue review pending** when a row exists.
- **Observed bounds**: Min/max **`current_price`** from listings linked to the model; compatible **`watch_sale_records`** (brand key + reference or family filters). Refreshed on model create/patch and after listing analyze; previous model refreshed when a listing’s link changes.
- **API**: **`/api/watch-models`** list ( **`q`**, pagination), CRUD; **`ListingDetail`** includes **`watch_model_id`** + brief **`watch_model`**.
- **UI**: Nav **Watch database**; listing detail **Watch catalog link** card + dropdown (up to 500 models).

---

## Planned / not done yet

| Item | Notes |
|------|--------|
| **Observed sale (O)** | Detect listing ended / capture last price via per-item Browse **getItem** or periodic refresh — not built. |
| **AI / search hooks (I, S)** | UI sources exist; no OpenAI or external watch DB integration. |
| **Reference-tight sale comps (listing bands)** | **`watch_models`** tie listings/sales by ref; **listing detail comp bands** still primarily brand (+ model family) — could tighten further using linked model. |
| **Saved searches** API/UI | Table exists for ingest lines only; no generic saved filter CRUD. |
| **Taxonomy**-driven ingest | Client stub only. |
| **Historical / multi-page** ingest | Offset pagination, dedupe across pages. |
| **Tests** | Unit/integration; stricter eBay **`invalid_scope`** handling if needed. |
| **npm audit** / Next upgrades | Per your policy. |

---

## Repository map (quick reference)

| Path | Role |
|------|------|
| `frontend/` | Next.js UI (static export) |
| `backend/watchfinder/main.py` | Entry, scheduler, routers, static mount |
| `backend/watchfinder/api/` | Routes, **`listing_detail.py`**, deps, query |
| `backend/watchfinder/schemas/` | Pydantic models |
| `backend/watchfinder/services/ebay/` | OAuth, Browse, Taxonomy, **`api_usage.py`** (persisted call counters) |
| `backend/watchfinder/services/ingestion/` | eBay → DB |
| `backend/watchfinder/services/ingest_settings.py` | Saved ingest queries + interval + **`ingest_search_limit`** |
| `backend/watchfinder/services/ingest_schedule.py` | APScheduler interval sync |
| `backend/watchfinder/services/valuation/` | Effective fields, comps, sale sync, field help |
| `backend/watchfinder/services/parsing/` | Corpus + attributes + keywords |
| `backend/watchfinder/services/repair/` | Signal extraction |
| `backend/watchfinder/services/scoring/` | Opportunity scoring |
| `backend/watchfinder/services/pipeline/` | `analyze_listing` |
| `backend/watchfinder/services/watch_models/` | Match, catalog create/backfill, candidates, link-review queue |
| `backend/watchfinder/services/watch_catalog_settings.py` | **`watch_catalog_review_mode`** (`auto` / `review`) |
| `backend/watchfinder/api/listing_sort.py` | Server-side listing sort for list/candidates APIs |
| `alembic/versions/` | **001**–**004** (includes **`watch_model_link_reviews`**) |
| `Dockerfile` / `docker/start.sh` / `docker-compose.yml` | Container workflow |
| `deploy/unraid/` | Unraid template(s) |
| `.github/workflows/docker-publish.yml` | GHCR |
| `Kickoff Documents/` | Unraid runbook + spec |

---

## How to continue

1. Implement **observed ingest (O)** when safe against rate limits.
2. Add **tests** for valuation PATCH, watch-model CRUD, and auto-link behavior.
3. Optional **saved filter** CRUD on `saved_searches` for UI list views.
4. Use **`watch_models`** (manual + observed bounds) in scoring or reporting when you define the formula.

For Unraid deployment, use **`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`**. After pulling a build that includes migrations through **004**, ensure the container runs **`alembic upgrade head`** (already in **`docker/start.sh`**).
