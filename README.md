# WatchFinder

Self-hosted eBay watch sourcing: **Browse API** ingest → **PostgreSQL** → rules-based repair signals and opportunity scores → **FastAPI** JSON API and **Next.js** web UI (static export, served on the **same port** as the API in Docker, default **8080**).

**Implementation status:** [`PROGRESS.md`](PROGRESS.md).

## Documentation map

| Document | Purpose |
|----------|---------|
| [`README.md`](README.md) (this file) | Quick start, API surface, Docker, Unraid summary, env vars |
| [`PROGRESS.md`](PROGRESS.md) | What is built (phases 1–4), repo map, backlog |
| [`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`](Kickoff%20Documents/SIMPLIFIED_NOVICE_SETUP.md) | Step-by-step Unraid install (folders, network, Postgres, app) |
| [`Kickoff Documents/README_START_HERE.txt`](Kickoff%20Documents/README_START_HERE.txt) | Kickoff folder index |
| [`Kickoff Documents/CURSOR_PROMPT.txt`](Kickoff%20Documents/CURSOR_PROMPT.txt) | Original full build spec (reference / Cursor) |
| [`deploy/unraid/watchfinder.xml`](deploy/unraid/watchfinder.xml) | Unraid template (paths, env vars — replace `YOUR_GITHUB_USERNAME`) |
| [`.env.example`](.env.example) | All configurable environment variables (comments) |

## Layout

- `frontend/` — Next.js 14 (App Router), TypeScript, Tailwind, shadcn-style UI
- `backend/watchfinder/` — FastAPI app, models, eBay clients, ingestion, parsing, scoring
- `alembic/` — database migrations
- `docker/start.sh` — wait for Postgres → `alembic upgrade head` → `uvicorn`
- `Dockerfile` — multi-stage image (Node build + Python runtime, non-root user, healthcheck)
- `docker-compose.yml` — local **postgres:16** + app build
- `deploy/unraid/watchfinder.xml` — Unraid template
- `.github/workflows/docker-publish.yml` — build & push to **GHCR**
- `Kickoff Documents/` — Unraid runbook + Cursor build spec

## User-facing URLs (when the stack is running)

| URL | What it is |
|-----|------------|
| `/` | Web UI (dashboard) |
| `/listings/` | Listings + filters |
| `/candidates/` | Repair candidates (positive rule-based profit) |
| `/settings/` | Ingest search lines, interval, **Ingest now** (same origin as API) |
| `/listings/detail/?id=<uuid>` | Listing detail (static export uses query string, not `/listings/<uuid>` in the browser) |
| `/api/...` | JSON API (same origin as UI in Docker) |
| `/docs` | Swagger UI |
| `/health` | Liveness JSON (`{"status":"ok"}`) — used by Docker **HEALTHCHECK** |

## API (quick reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/dashboard` | Totals, candidate count, repair-signal count, recent listings |
| GET | `/api/listings` | Paginated listings + query filters |
| GET | `/api/listings/{uuid}` | Detail (API uses path param; UI detail page uses `?id=` + this endpoint) |
| GET | `/api/candidates` | Same filters as listings; only rows with `potential_profit > 0` |
| GET | `/api/settings` | Ingest interval, saved Browse query lines, env fallback hint |
| PATCH | `/api/settings` | Update interval (5–1440) and/or replace all ingest query lines |
| POST | `/api/ingest/run` | Queue a full ingest cycle in the background (check logs) |

## Ingest searches (UI + API)

- **Web UI:** **`/settings/`** — add multiple **Browse** keyword lines (each line = one `q` sent to eBay). Combine words on a line for a single search; use several lines for different angles (brands, “spares / not working”, military, etc.). Disabled lines are skipped. If there are **no** saved lines (or every line is empty), ingest uses **`EBAY_SEARCH_QUERY`** from the environment.
- **Interval:** Stored in **`app_settings`** when changed from the UI; otherwise **`INGEST_INTERVAL_MINUTES`** from env. Changing interval in **Settings** reschedules the job without restarting the container.
- **Ingest now:** Calls **`POST /api/ingest/run`** (background task). There is **no authentication** on these endpoints — intended for trusted LAN / self-hosted use only.

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

## Docker Compose (local full stack)

1. Copy **`.env.example`** → **`.env`** and set **`EBAY_CLIENT_ID`** and **`EBAY_CLIENT_SECRET`** (Compose substitutes variables from `.env`).
2. Run:

```bash
docker compose up --build
```

- App + UI: **http://localhost:8080**
- Postgres: **localhost:5432** (default user/password/db **`watchfinder`** — change for anything beyond local dev)

The compose file uses the Docker service name **`postgres`** in `DATABASE_URL`, not `watchfinder-postgres` (that name is for Unraid parity).

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
| `EBAY_SEARCH_QUERY` / `EBAY_SEARCH_LIMIT` | Scheduled Browse search (limit 1–200) |
| `EBAY_CATEGORY_TREE_ID` | Optional taxonomy tree id |
| `TZ` | Container timezone |
| `APP_PORT` | Uvicorn listen port (match published port; healthcheck uses this) |
| `LOG_LEVEL` | Python logging level |
| `INGEST_INTERVAL_MINUTES` | Minutes between ingest jobs (5–1440) |

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
- **Ingest** runs on an interval inside the app (**APScheduler**); tune **`INGEST_INTERVAL_MINUTES`** and search fields via env.
- **Tuning rules:** repair phrases **`backend/watchfinder/services/parsing/keywords.py`**; scoring economics **`backend/watchfinder/services/scoring/constants.py`**.
