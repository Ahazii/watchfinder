# WatchFinder

Self-hosted eBay watch sourcing: **Browse API** ingest → **PostgreSQL** → rules-based repair signals and opportunity scores → **FastAPI** JSON API and **Next.js** web UI (static export, served on the **same port** as the API in Docker, default **8080**).

**Implementation status:** [`PROGRESS.md`](PROGRESS.md).

## Documentation map

| Document | Purpose |
|----------|---------|
| [`README.md`](README.md) (this file) | Quick start, API surface, Docker, Unraid summary, env vars |
| [`PROGRESS.md`](PROGRESS.md) | What is built (phases 1–6), repo map, backlog, planned work |
| [`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`](Kickoff%20Documents/SIMPLIFIED_NOVICE_SETUP.md) | Step-by-step Unraid install (folders, network, Postgres, app) |
| [`Kickoff Documents/README_START_HERE.txt`](Kickoff%20Documents/README_START_HERE.txt) | Kickoff folder index |
| [`Kickoff Documents/CURSOR_PROMPT.txt`](Kickoff%20Documents/CURSOR_PROMPT.txt) | Original full build spec (reference / Cursor) |
| [`deploy/unraid/watchfinder.xml`](deploy/unraid/watchfinder.xml) | Unraid template (paths, env vars — replace `YOUR_GITHUB_USERNAME`) |
| [`.env.example`](.env.example) | All configurable environment variables (comments) |

## Layout

- `frontend/` — Next.js 14 (App Router), TypeScript, Tailwind, shadcn-style UI
- `backend/watchfinder/` — FastAPI app, models, eBay clients, ingestion, parsing, scoring
- `alembic/` — database migrations through **008** (**`market_source_snapshots`**; **007** WatchBase import JSON; **006** specs + **`reference_url`**; **005** **`ebay_item_id`**)
- `docker/start.sh` — wait for Postgres → `alembic upgrade head` → `uvicorn`
- `Dockerfile` — multi-stage image (Node build + Python runtime, non-root user, healthcheck)
- `docker-compose.yml` — local **postgres:16** + app build
- `deploy/unraid/watchfinder.xml` — Unraid template
- `.github/workflows/docker-publish.yml` — build & push to **GHCR**
- `Kickoff Documents/` — Unraid runbook + Cursor build spec

## User-facing URLs (when the stack is running)

| URL | What it is |
|-----|------------|
| `/` | Dashboard (stats, **eBay Browse / OAuth call counters**, recent listings with thumbs) |
| `/listings/` | Listings + filters (**Title contains**, brand, price, etc.), sortable columns, thumbnails |
| `/candidates/` | Repair candidates (same filters as listings where applicable) |
| `/settings/` | Browse search lines, **interval** + **items per search line** (1–200), **stale listing refresh** (optional scheduler), **match queue sync** interval (re-process active listings with no catalog link), watch-catalog mode, **Ingest now** / **Stale refresh now** |
| `/watch-models/` | **Watch database** — catalog CRUD (canonical models, manual + observed price bounds) |
| `/watch-models/detail/?id=<uuid>` | Edit one model (all fields); optional **Everywatch watch URL** (exact listing page) drives snapshots and market search; omit `id` to create; **Everywatch import tester** link opens **`/watch-models/everywatch-test/?id=`** for debug fetches |
| `/watch-models/everywatch-test/?id=<uuid>` | Debug Everywatch HTML / mapping (optional Cookie header): **`/watch-listing?query=…`** probes, parsed hit table, detail **specs / image / GBP price rows**; does not import into catalog |
| `/watch-review/` | **Match queue** — pending catalogue links (review mode) |
| `/watch-review/detail/?id=<review-uuid>` | Resolve one queue item (match / create / dismiss) |
| `/listings/detail/?id=<uuid>` | Listing detail, **editable valuation**, **watch catalog link** (override / clear), internal comps, **Save** → `PATCH /api/listings/{id}` |
| `/api/...` | JSON API (same origin as UI in Docker) |
| `/docs` | Swagger UI |
| `/health` | Liveness JSON (`{"status":"ok"}`) — used by Docker **HEALTHCHECK** |

## API (quick reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/dashboard` | Totals, candidate count, repair-signal count, recent listings (each with **`image_urls`**), plus persisted eBay counters (**`ebay_browse_search_calls`**, **`ebay_oauth_token_calls`**, **`ebay_browse_get_item_calls`**); see [eBay REST rate limiting](https://developer.ebay.com/api-docs/static/rest-rate-limiting-API.html) |
| GET | `/api/listings` | Paginated listings + query filters (**`title_q`**, brand, price, repair, **`listing_active`**: `active` / `inactive` / `all`, **`exclude_quartz`**, etc.); rows include **`image_urls`**, **`is_active`**; **`sort_by`** / **`sort_dir`** — see OpenAPI |
| GET | `/api/listings/{uuid}` | Detail + comps + editable valuation fields (`source_legend`, `field_guidance`) |
| PATCH | `/api/listings/{uuid}` | Save **ListingEdit** + optional **`watch_model_id`** (`null` unlinks; re-analyze runs catalog match/create when unset) |
| POST | `/api/listings/{uuid}/promote-watch-catalog` | **Save to watch database** for one listing: match existing catalog row or **create** one from brand + reference (or brand + family) |
| POST | `/api/listings/{uuid}/refresh-from-ebay` | Browse **getItem** for this row: refresh price/title/images; **`404`** → set **`is_active=false`** (listing drops off default lists) |
| GET | `/api/watch-models` | Paginated catalog (`skip`/`limit`). **`q`** — case-insensitive substring OR across brand, reference, model family, model name. Optional **AND** filters (contains): **`brand`**, **`reference`**, **`model_family`**, **`model_name`**, **`caliber`**. **`pricing`**: `all` (default), **`has_signal`** (any manual/observed £ or WatchBase points), **`missing_signal`**, **`strict_needs`** / **`strict_ok`** (batch “without pricing” rule). **`import_status`**: `all`, **`unmatched`** (no **`reference_url`** or never **`watchbase_imported_at`**), **`matched`**. Brands in **`WATCH_CATALOG_EXCLUDED_BRANDS`** are omitted from this list (and from listing link pickers using the same API). Rows include **`linked_ebay_urls`** and specs |
| POST | `/api/watch-models` | Create model |
| POST | `/api/watch-models/backfill-from-listings` | Scan active listings; link or create catalog rows (same rules as ingest analyze) |
| GET | `/api/watch-link-reviews` | Pending match-queue rows (`skip`/`limit`) |
| POST | `/api/watch-link-reviews/sync-from-unmatched` | Re-analyze every **active** listing with **no** `watch_model_id` (same rules as ingest **analyze**): in **review** mode, eligible rows enqueue; in **auto** mode, link or create catalog rows. Returns the same counter object as **`…/backfill-from-listings`** |
| GET | `/api/watch-link-reviews/{uuid}` | One queue item + scored candidate models |
| POST | `/api/watch-link-reviews/{uuid}/resolve` | Body `{ "action": "match"|"create"|"dismiss", "watch_model_id"?: uuid }` |
| GET | `/api/watch-models/{uuid}` | One model; includes **`linked_ebay_urls`** (active linked listings’ **`web_url`** values) |
| PATCH | `/api/watch-models/{uuid}` | Update model (observed bounds refreshed after save) |
| GET | `/api/watchbase/search?q=…` | Proxies WatchBase **`/filter/results?q=`** (their on-site search). Returns watch page URLs + labels for the find wizard. **`WATCHBASE_IMPORT_ENABLED=false`** disables |
| POST | `/api/everywatch/debug` | **Dev / LAN:** body **`watch_model_id`?**, **`extra_urls`[]** (tried first), **`search_queries`[]** (includes **`/watch-listing`** URLs), **`cookie_header`?** (browser Cookie after login — not stored). Returns **`analysis`** with **`parsed_listing_hits_sample`**, **`detail_import_preview`** on watch pages, plus **`collect_everywatch_snapshot`**. Does not write DB |
| GET | `/api/market/search` | Unified search: **`q`** (required) plus optional **`brand`**, **`reference`**, **`model_family`**, **`everywatch_url`** (exact Everywatch watch page — same as saved on **`watch_models`**) — WatchBase filter hits, Everywatch listing/detail fetch + **price hints** (HTML parse), Chrono24 **search URL** + Google `site:` link and optional hits if HTML is not blocked. **`WATCHBASE_IMPORT_ENABLED=false`** leaves the WatchBase bucket empty |
| POST | `/api/watch-models/{uuid}/refresh-market-snapshots` | Fetches Everywatch model page(s) + attempts Chrono24 search; stores **`market_source_snapshots`** JSONB. On a **watch detail** URL, fills **empty** **`spec_*`** / **`caliber`** / **`image_urls`** from parsed Everywatch HTML when possible. If **manual £ low/high** are missing, seeds them from Everywatch **GBP** values when present (detail **`price_analysis`** / listing hit amounts); otherwise falls back to **median** non-GBP → GBP (Frankfurter) with a ±10% band (only when **both** manual fields were empty). **`EXTRA_MARKET_IMPORT_ENABLED=false`** returns failure. Respects **`MARKET_SNAPSHOT_COOLDOWN_HOURS`** only for automatic runs; this POST is **force** refresh |
| POST | `/api/watch-models/{uuid}/import-watchbase` | Body optional `{"reference_url": "…"}` (uses saved DB URL if omitted). Fetches WatchBase HTML + **`/prices`** JSON; fills specs, **`external_price_history`**; **Family** row → **`model_family`**; EUR chart min/max → **`manual_price_low` / `manual_price_high`** in **GBP** (Frankfurter API, or **`EUR_GBP_RATE_FALLBACK`**). **`WATCHBASE_IMPORT_ENABLED=false`** disables |
| DELETE | `/api/watch-models/{uuid}` | Delete (listings unlinked via FK **SET NULL**) |
| GET | `/api/candidates` | Same filters and **sort** as listings (**`listing_active`**, **`exclude_quartz`**, etc.); only rows with `potential_profit > 0`. Summary rows include **`watch_model_id`** when linked. **Scoring (analyze):** if the listing is linked to **`watch_models`** and that row has **manual** or **observed** £ bounds, **estimated resale** uses that **working-market anchor** (manual midpoint/high preferred over observed; **parts** signals use ×0.55 on the anchor). Asking price is converted **→ GBP** via [Frankfurter](https://www.frankfurter.app/) (cached ~1h per currency); profit and resale are converted back to the **listing currency** for storage/display. If FX fails or the listing is unlinked / has no bounds, the **list price × category multiplier** heuristic is used. Re-run **analyze** (ingest or listing refresh path) to refresh scores after catalog or price changes |
| GET | `/api/settings` | Ingest interval, **`ebay_search_limit`**, **`ingest_max_pages`**, stale-refresh toggles (**`stale_listing_refresh_*`**), **`match_queue_sync_interval_minutes`** (0–1440; **0** = scheduler off), saved Browse query lines, **`watch_catalog_excluded_brands`**, optional **Everywatch** **`everywatch_login_email`** + **`everywatch_password_configured`** (password never returned), env fallback hint |
| PATCH | `/api/settings` | Same fields as GET: interval, limits, pages, ingest lines, **`watch_catalog_review_mode`**, **`watch_catalog_excluded_brands`**, **`everywatch_login_email`**, **`everywatch_login_password`** (omit to keep; **`""`** clears), **`stale_listing_refresh_enabled`**, interval/max-per-run/min-age for stale batch, **`match_queue_sync_interval_minutes`** |
| POST | `/api/ingest/run` | Queue a full ingest cycle in the background (check logs) |
| POST | `/api/ingest/stale-refresh-run` | Queue one batch of **getItem** refreshes for stale **active** listings (see Settings) |

## Valuation & internal comps (hobby use)

- **No eBay sold-history API:** comps use only data in **your** Postgres: **`watch_sale_records`** (built when you enter a **recorded sale** on a listing) and **active** listings with the same **parsed brand** for asking-price bands (p25–p75).
- **Watch catalog (`watch_models`):** one row per canonical watch type (brand + reference when present, else brand + model family). **Many listings** can share one **`watch_model_id`**. **Observed** low/high prices are derived from linked listings (and compatible sale records); **manual** low/high are editable on the model — both are stored for future calculations. **Settings → Watch catalog matching:** **`auto`** = full pipeline on each **analyze** (exact + fuzzy title + auto-create). **`review`** = exact brand+ref / brand+family only; other cases go to **`watch_model_link_reviews`** and the **Match queue** UI (scored candidates; **Match** / **Create new** / **Dismiss**). **Backfill** follows the same mode; **promote** always bypasses the queue. Override **`watch_model_id`** on the listing detail page when the link is wrong.
- **Match queue sync:** Active listings still **unlinked** (`watch_model_id` null) are picked up by a scheduled job (**`match_queue_sync`**, interval from **`MATCH_QUEUE_SYNC_INTERVAL_MINUTES`** / Settings **`match_queue_sync_interval_minutes`**; **0** disables). The job runs the same **analyze** path as ingest. Use **`POST /api/watch-link-reviews/sync-from-unmatched`** or the **Match queue** page button for an immediate pass. Listings without parseable brand + (reference or model family) stay skipped until titles or manual **ListingEdit** fields improve identity.
- **Listing detail (`/listings/detail/?id=`)** — editable fields with **source** dropdown per field: **M** manual, **I** inferred (AI — hook later), **S** searched, **R** rules/parsed text, **O** observed ingest (reserved for future “listing ended” detection), **H** historical, **P** parsed (same idea as R). Guidance strings are returned as **`field_guidance`** on the detail JSON.
- **Repair:** rule-based core **plus** optional **repair add-on** and **donor cost** (both included in total repair for profit math). Fees/shipping ignored.
- **Tuning asking-sample size:** optional **`app_settings`** row **`max_comp_candidates`** (integer string, default **200** in code if unset).

### UI: currencies and on-screen help

- **`watch_models`** **manual** and **observed** bounds are stored and displayed in **GBP (£)**. **WatchBase** chart points stay in **EUR (€)** in the imported table; import converts min/max to GBP for manual bounds when FX works.
- **eBay listings** use **that item’s currency** for price, shipping, opportunity score lines, and (for consistency) your per-listing valuation inputs — see symbols in cells (**`money()`** in `frontend/lib/format.ts` defaults to GBP only when no valid ISO code is passed).
- **List / candidate price filters** compare **numeric** amounts as stored; they do not convert currencies.
- **Settings** includes a **“Prices & currencies in the UI”** card; listing, watch, dashboard, and match-queue pages use **CardDescription** text and table header **tooltips** where prices appear.
- **Watch database (`/watch-models/`):** **Search and filters** card — global **`q`** plus contains fields (brand, reference, model family, model name, caliber), **Price data** (any/missing/strict), and **WatchBase** (unmatched/matched). **`WATCH_CATALOG_EXCLUDED_BRANDS`** hides brands server-side. Presets use the same filters plus fixed criteria for unmatched / strict pricing gaps. **Rows per page** — **25**, **50**, **100**, **200**, **500**, or **All** (loads every row matching current filters via repeated API calls; choice persisted in **`localStorage`** key **`watchfinder-watch-models-page-size`**). **Delete selected** (batch card) removes all checked rows using **`DELETE /api/watch-models/{uuid}`** (listings unlinked). **Find on markets…** (model detail) and the supervised **batch** wizard call **`GET /api/market/search`** — WatchBase filter hits, **Everywatch** listing URLs + parsed **price hints**, and **Chrono24** search + Google links (automated Chrono24 HTML often returns **403**; use browser). **`market_source_snapshots`** JSON is filled on **analyze** / **backfill** and via **Refresh market snapshots**; comply with each site’s terms. Supervised wizard: side-by-side images, **Delete this catalog entry**, paste WatchBase URL for import, **No match — skip**; jittered delays between WatchBase calls.

After upgrading, run **`alembic upgrade head`** (through **008** / market snapshots + WatchBase import columns + prior migrations).

### Listing `is_active` and live checks

- **`listings.is_active`** is set **`true`** when an item appears in Browse **ingest** results or when **`POST /api/listings/{id}/refresh-from-ebay`** returns a live **getItem** payload.
- **`is_active`** is set **`false`** when **getItem** returns **404** (ended / removed from Buy Browse). Use **Refresh from eBay** on the listing detail page, **`POST /api/listings/{id}/refresh-from-ebay`**, or a **stale listing refresh** batch when **getItem** returns 404 for that row. Ingest search alone does **not** mark missing rows inactive (an item can leave your result set but still be live).
- **Listings** / **candidates** list APIs default to **`listing_active=active`** (active rows only). Use **`listing_active=all`** or **`inactive`** to include or isolate ended listings. **Detail** still returns inactive rows so you can refresh or read history.

## Ingest searches (UI + API)

- **Web UI:** **`/settings/`** — add multiple **Browse** keyword lines (each line = one `q` per ingest cycle). Tune **items per search line** (1–200 → **`app_settings.ingest_search_limit`**), **pages per line** (1–20 → **`app_settings.ingest_max_pages`**; each extra page is another **`item_summary/search`** with `offset += limit`), and **interval minutes**. Optional **stale listing refresh**: scheduled batch **getItem** for active rows whose **`last_seen_at`** is null or older than **min age** hours (capped per run; **0** = any timestamp in the past — useful right after ingest); env **`STALE_LISTING_REFRESH_*`** until saved. Optional **match queue sync**: re-analyze active listings with no catalog link on an interval (**`app_settings.match_queue_sync_interval_minutes`**; **0** = off); env **`MATCH_QUEUE_SYNC_INTERVAL_MINUTES`** until saved. Rough ceiling per ingest cycle ≈ *limit × pages × enabled lines* Browse calls. Env defaults: **`EBAY_SEARCH_LIMIT`**, **`INGEST_MAX_PAGES`**, until saved. If there are **no** saved lines (or every line is empty), ingest uses **`EBAY_SEARCH_QUERY`** from the environment.
- **Interval:** Stored in **`app_settings.ingest_interval_minutes`** when changed from the UI; otherwise **`INGEST_INTERVAL_MINUTES`** from env. Changing interval in **Settings** reschedules the job without restarting the container.
- **OAuth (one token per ingest cycle, one per stale batch):** A single **`EbayAuthClient`** + **`EbayBrowseClient`** is reused for **all** query lines in one scheduled or **Ingest now** run. The same pattern applies to **stale listing refresh** (scheduled or **Stale refresh now**): **one** shared client for **all** **getItem** calls in that batch, so you should not see a token POST per listing. Dashboard counters **`ebay_oauth_token_calls`** / **`ebay_browse_search_calls`** / **`ebay_browse_get_item_calls`** persist in **`app_settings.ebay_api_usage_json`** (token increments on each successful refresh from eBay, not on cache hits).
- **Ingest now:** Calls **`POST /api/ingest/run`** (background task). **Stale refresh now** calls **`POST /api/ingest/stale-refresh-run`**. There is **no authentication** on these endpoints — intended for trusted LAN / self-hosted use only.

## Local development

Requires **Python 3.12+**, **Node 20+** (for the UI), and **PostgreSQL 16** (local or Docker).

**1. API + Postgres**

Windows (PowerShell / cmd):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
set PYTHONPATH=backend
alembic upgrade head
uvicorn watchfinder.main:app --reload --host 0.0.0.0 --port 8080
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=backend
alembic upgrade head
uvicorn watchfinder.main:app --reload --host 0.0.0.0 --port 8080
```

Edit **`.env`** with a valid `DATABASE_URL` and eBay credentials.

**2. Frontend (optional hot reload)**

```bash
cd frontend
npm install
```

Set **`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080`** (Windows: `set`, Linux/mac: `export`), then:

```bash
npm run dev
```

Open **http://localhost:3000**.

**3. Production-like (UI baked in, single port)**

```bash
cd frontend && npm install && npm run build
export PYTHONPATH=backend   # or set PYTHONPATH=backend on Windows
uvicorn watchfinder.main:app --host 0.0.0.0 --port 8080
```

Open **http://localhost:8080**. Do **not** set `NEXT_PUBLIC_API_BASE` so the browser calls same-origin `/api/...`.

**Backend tests (optional):** `pip install -r requirements-dev.txt` then **`pytest`** from the repo root (`pytest.ini` sets `pythonpath = backend`).

## Docker Compose (local full stack)

1. Copy **`.env.example`** → **`.env`** and set **`EBAY_CLIENT_ID`** and **`EBAY_CLIENT_SECRET`** (Compose substitutes variables from `.env`).
2. Run:

```bash
docker compose up --build
```

- App + UI: **http://localhost:8080**
- Postgres: **localhost:5432** (default user/password/db **`watchfinder`** — change for anything beyond local dev)

The compose file uses the Docker service name **`postgres`** in `DATABASE_URL`, not `watchfinder-postgres` (that name is for Unraid parity).

**Watch images:** eBay gallery photos for linked catalog rows are downloaded into the named volume mounted at **`LOCAL_MEDIA_ROOT`** (default **`/data/media`** in Compose) and served at **`/api/media/...`**. Persist this volume on Unraid so thumbnails survive container recreation.

## CI/CD — GitHub Container Registry

- Workflow: **`.github/workflows/docker-publish.yml`**
- Triggers: push to **`main`** (image tag **`latest`**), tags **`v*`** , **workflow_dispatch**
- Image: **`ghcr.io/<github-username-or-org>/watchfinder`**
- Builds **`linux/amd64`** (typical Unraid host).
- **Private packages on Unraid:** use a GitHub [PAT](https://github.com/settings/tokens) with **`read:packages`** and configure **`ghcr.io`** credentials on Unraid.

## Unraid installation

Full walkthrough: **[`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`](Kickoff%20Documents/SIMPLIFIED_NOVICE_SETUP.md)**.

Short checklist:

1. Create folders under **`/mnt/user/appdata/`** (see runbook).
2. **`docker network create watchfinder-net`**; attach **Postgres** and **WatchFinder** to it.
3. **Postgres:** image **`postgres:16`**, container name **`watchfinder-postgres`**, data path as in runbook.
4. Ensure **GitHub Actions** has published **`ghcr.io/<you>/watchfinder:latest`**.
5. **WatchFinder:** use **`deploy/unraid/watchfinder.xml`** as a checklist (replace **`YOUR_GITHUB_USERNAME`**). Set all template variables; **`DATABASE_URL`** must use host **`watchfinder-postgres`** and the same password as **`POSTGRES_PASSWORD`**.
6. Start **Postgres** first, then **WatchFinder**.
7. Open **`http://<unraid-ip>:8080/`** (UI) and **`/docs`** for API.

Do **not** rely on building the app from Git on the Unraid server for production; pull the image from **GHCR**.

## Environment variables

Full list and comments: **[`.env.example`](.env.example)**. On Unraid, set the same variable **names** in the container template (there is no `.env` file inside the image for those).

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://user:pass@host:5432/db`) |
| `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` | eBay application credentials |
| `EBAY_ENVIRONMENT` | `production` or `sandbox` |
| `EBAY_MARKETPLACE_ID` | e.g. `EBAY_GB`, `EBAY_US` |
| `EBAY_SEARCH_QUERY` / `EBAY_SEARCH_LIMIT` | Default Browse `q` and per-search page size (1–200); UI persists **`app_settings.ingest_search_limit`** |
| `INGEST_MAX_PAGES` | Default number of search result pages per query line (1–20); UI persists **`app_settings.ingest_max_pages`** |
| `EBAY_CATEGORY_TREE_ID` | Optional taxonomy tree id |
| `TZ` | Container timezone |
| `APP_PORT` | Uvicorn listen port (match published port; healthcheck uses this) |
| `LOG_LEVEL` | Python logging level |
| `INGEST_INTERVAL_MINUTES` | Default minutes between ingest jobs (5–1440); UI can persist override in **`app_settings.ingest_interval_minutes`** |
| `WATCHBASE_IMPORT_ENABLED` | Allow **`POST …/import-watchbase`** (default **true**) |
| `WATCHBASE_HTTP_USER_AGENT` | Optional User-Agent for WatchBase HTTP requests |
| `EUR_GBP_RATE_FALLBACK` | Optional GBP-per-EUR rate if Frankfurter FX API fails during import (e.g. **0.85**) |
| `LOCAL_MEDIA_ROOT` / `MEDIA_DOWNLOAD_*` | Cached listing images for catalog thumbs (see **`.env.example`**) |
| `STALE_LISTING_REFRESH_*` | Stale **getItem** batch defaults until overridden in Settings (see **`.env.example`**) |
| `MATCH_QUEUE_SYNC_INTERVAL_MINUTES` | Default minutes between **match queue sync** jobs (0–1440; **0** = no scheduled job). UI persists **`app_settings.match_queue_sync_interval_minutes`** |

Optional for **local Next dev only:** `NEXT_PUBLIC_API_BASE` (see Local development above).

## eBay

### Developer account and approval

1. Sign in at the [eBay Developers Program](https://developer.ebay.com/) with your normal eBay account (or a dedicated one if you prefer).
2. eBay may require **account verification or application approval** before you can create production keysets or use certain **Buy** APIs. **Approval is not instant** — you can run WatchFinder (UI, Postgres, health) while you wait, but **scheduled ingest will not pull live listings** until you have valid **Client ID** and **Client Secret** and **Browse API** access.
3. When authorized, create an **application** and copy **Client ID** and **Client Secret** into **`EBAY_CLIENT_ID`** and **`EBAY_CLIENT_SECRET`**. Ensure the app is allowed to use **Buy Browse** (and that **`EBAY_ENVIRONMENT`** matches where the keys were issued: **`production`** vs **`sandbox`**).
4. OAuth scopes for client credentials are implemented in **`backend/watchfinder/services/ebay/auth.py`** — adjust only if eBay returns **`invalid_scope`** (see current eBay OAuth docs for Browse).

### While you wait

- Use placeholder values in env vars only if you accept **ingest errors** in logs every **`INGEST_INTERVAL_MINUTES`**; the web UI and API still load.
- After eBay activates your access, update the container env vars and **restart** WatchFinder (or redeploy). Check logs on the next ingest run for Browse/token errors.

## Operations notes

- **Migrations** run automatically on container start (`docker/start.sh` → `alembic upgrade head`).
- **Ingest** runs on an interval inside the app (**APScheduler**). Tune **interval** and **items per search line** in **`/settings/`** (persisted in **`app_settings`**), or use **`INGEST_INTERVAL_MINUTES`** / **`EBAY_SEARCH_LIMIT`** as defaults before the first save. Search **lines** are edited in the same UI (stored in **`saved_searches`**). **Match queue sync** and **stale listing refresh** are separate scheduler jobs (enable/tune in Settings; see **`.env.example`**).
- **Tuning rules:** repair phrases **`backend/watchfinder/services/parsing/keywords.py`**; scoring economics **`backend/watchfinder/services/scoring/constants.py`**.
