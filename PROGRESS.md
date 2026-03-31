# WatchFinder — implementation progress

Last updated: **31 March 2026**

This document records what is implemented in the repository versus the phased plan in **`Kickoff Documents/CURSOR_PROMPT.txt`**.

**Where to read what**

| Topic | Document |
|-------|----------|
| Run locally, Docker, CI, Unraid summary | Root **`README.md`** |
| Step-by-step Unraid (novice) | **`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`** |
| Unraid XML field list | **`deploy/unraid/watchfinder.xml`** |
| Environment variables | **`.env.example`** |
| Original full spec | **`Kickoff Documents/CURSOR_PROMPT.txt`** |

---

## Summary

| Phase | Scope (from prompt) | Status |
|-------|----------------------|--------|
| **1** | Backend skeleton, models, Alembic, config, eBay clients, ingestion, startup | **Done** |
| **2** | Parsing, repair keywords, scoring + explanations, API routes | **Done** |
| **3** | Next.js 14 UI (dashboard, listings, detail, candidates), Tailwind, shadcn-style components | **Done** |
| **4** | Dockerfile, `.env.example`, GitHub Actions, Unraid XML, README, compose | **Done** |

---

## Phase 1 (complete)

- **FastAPI** app in `backend/watchfinder/main.py` with lifespan, **`GET /health`**, and **APScheduler** running Browse ingest on `INGEST_INTERVAL_MINUTES`.
- **Settings** via `pydantic-settings` (`watchfinder/config.py`): `DATABASE_URL`, eBay credentials, marketplace, search query/limit, etc.
- **PostgreSQL** via SQLAlchemy 2 + **psycopg** (`watchfinder/db.py`).
- **Models** (`watchfinder/models/listing.py`): `listings`, `listing_snapshots`, `parsed_attributes`, `repair_signals`, `opportunity_scores`, `saved_searches`, `app_settings`.
- **Alembic** initial migration: `alembic/versions/001_initial_schema.py`.
- **eBay**: client-credentials OAuth (`services/ebay/auth.py`), **Browse** item summary search (`browse.py`), **Taxonomy** client stub (`taxonomy.py`).
- **Ingestion**: map item summaries → listing rows + snapshots (`services/ingestion/mapper.py`, `job.py`).
- **Docker**: `docker/start.sh` (wait for Postgres with URL-safe `postgresql://`, `alembic upgrade head`, `uvicorn`).
- **CI**: `.github/workflows/docker-publish.yml` → **GHCR** `ghcr.io/<repo_owner>/watchfinder`.
- **Deploy template**: `deploy/unraid/watchfinder.xml` (paths under `/mnt/user/appdata/...`).
- **Kickoff docs**: `Kickoff Documents/` (novice Unraid runbook + single Cursor prompt).

---

## Phase 2 (complete)

- **Parsing** (`services/parsing/`): corpus assembly; rules-first **brand / reference / movement / caliber / running_state**; tunable **repair phrase** list in `keywords.py`.
- **Repair signals** (`services/repair/extract.py`): non-overlapping phrase matches → stored `repair_signals` rows.
- **Scoring** (`services/scoring/`): rule-based resale/repair/margin math, **confidence**, **risk**, **explanations** JSON; tunable numbers in `constants.py`.
- **Pipeline** (`services/pipeline/analyze.py`): after each listing upsert in ingest, clears and repopulates parsed attributes, signals, and **at most one** current opportunity score row per listing (when repair signals exist).
- **REST API** (prefix `/api`):
  - `GET /api/dashboard`
  - `GET /api/listings` (+ query filters)
  - `GET /api/listings/{uuid}`
  - `GET /api/candidates` (profit > 0)
- **Query layer** (`api/query.py`, `listing_helpers.py`) avoids duplicate rows from joins by using `EXISTS` subqueries.

OpenAPI: **`/docs`** (FastAPI) when the app is running.

---

## Phase 3 (complete)

- **`frontend/`** — Next.js 14 **App Router**, **TypeScript**, **Tailwind**, **shadcn-style** primitives (`components/ui/`: Button, Card, Input, Badge, Table), **DM Sans** font, dark theme.
- **Static export** (`output: "export"`) → `frontend/out/`; **FastAPI** mounts that directory at **`/`** when present (after `/api`, `/health`, `/docs`), so **one container / one port (8080)** serves UI + API.
- **Pages**:
  - **`/`** — Dashboard (stats + recent listings).
  - **`/listings/`** — Filterable table, pagination, **Apply** to run query.
  - **`/listings/detail/?id=`** — Detail (eBay link, score, explanations, signals, parsed attrs). Query-param URL avoids dynamic `[id]` export limitations.
  - **`/candidates/`** — Profit-positive subset with light filters.
- **CORS** `allow_origins=["*"]` for simple cross-origin use (e.g. tooling).
- **Local UI dev**: run API on **8080**, then `cd frontend && set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080 && npm run dev` (port **3000**). Production / Docker: leave **`NEXT_PUBLIC_API_BASE` unset** so the browser uses same-origin `/api/...`.

---

## Phase 4 (complete)

- **`Dockerfile`**: multi-stage Node + Python; OCI **labels** + **`VERSION` build-arg** (set from CI); **`HEALTHCHECK`** on `/health` (respects `APP_PORT`); runs as non-root user **`watchfinder`** (uid 1000); strips **build-essential** after `pip install` to shrink layers.
- **`.env.example`**: commented groups; all backend settings documented; note that Unraid uses template envs, not this file in-container.
- **`.github/workflows/docker-publish.yml`**: GHCR login + **Buildx** + **GHA cache** (`cache-from` / `cache-to`); **concurrency** group; **`VERSION=${{ github.sha }}`** passed as build-arg.
- **`deploy/unraid/watchfinder.xml`**: port **8080**, all path mappings, **DATABASE_URL**, eBay vars, **`EBAY_SEARCH_LIMIT`**, **`INGEST_INTERVAL_MINUTES`**, **`APP_PORT`**, **`LOG_LEVEL`**, **`EBAY_CATEGORY_TREE_ID`**; overview points to **`SIMPLIFIED_NOVICE_SETUP.md`** and **`watchfinder-net`**.
- **`docker-compose.yml`**: **postgres:16** + app **build**; healthcheck on Postgres; ready for local smoke tests with `.env` providing eBay keys.
- **`README.md`**: **Unraid installation** summary, **CI/CD / GHCR**, **Docker Compose**, **environment variable** table, private package pull note.

---

## Not done yet

- **Saved searches** API/UI (table exists; no routes).
- **Taxonomy** used for category-driven ingest (client exists; ingest uses text search query).
- **Historical / multi-page** ingest (offset pagination, dedupe across pages).
- **Tests** (unit/integration) and stricter eBay scope handling if `invalid_scope` appears in production.
- **Dependency hygiene**: run `npm audit` / upgrade Next when your policy requires a newer patched release.

---

## Repository map (quick reference)

| Path | Role |
|------|------|
| `frontend/` | Next.js UI (static export) |
| `backend/watchfinder/` | Application package |
| `backend/watchfinder/main.py` | App entry, scheduler, CORS, static mount, `/api` routers |
| `backend/watchfinder/api/` | Routes, deps, listing query helpers |
| `backend/watchfinder/schemas/` | Pydantic response models |
| `backend/watchfinder/services/ebay/` | OAuth, Browse, Taxonomy |
| `backend/watchfinder/services/ingestion/` | eBay → DB |
| `backend/watchfinder/services/parsing/` | Corpus + attributes + keywords |
| `backend/watchfinder/services/repair/` | Signal extraction |
| `backend/watchfinder/services/scoring/` | Opportunity scoring |
| `backend/watchfinder/services/pipeline/` | `analyze_listing` after ingest |
| `alembic/` | Migrations |
| `Dockerfile` | Multi-stage production image |
| `docker/start.sh` | Container entry |
| `docker-compose.yml` | Local Postgres + app |
| `deploy/unraid/watchfinder.xml` | Unraid template |
| `.github/workflows/docker-publish.yml` | GHCR build and push |
| `.dockerignore` | Slimmer Docker build context |
| `Kickoff Documents/` | Unraid runbook + Cursor spec |

---

## How to continue

1. Harden **ingest** (pagination, rate limits, error metrics).
2. Add **tests** and optional **saved_searches** CRUD.
3. Keep **Next.js** on a supported line per `npm audit` / vendor advisories.

For Unraid deployment steps, use **`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`**.
