# WatchFinder — Unraid setup (beginner)

Two **Docker** containers on Unraid (not a VM): **PostgreSQL** (`postgres:16`) and **WatchFinder** (image from **GitHub Container Registry**).

**Order:** create folders → create Docker network **`watchfinder-net`** → add Postgres → (after GHCR has an image) add WatchFinder.

**Related docs:** project root **`README.md`** (overview, CI/CD, env vars, watch catalog API), **`deploy/unraid/watchfinder.xml`** (full template with all variables), **`PROGRESS.md`** (feature status, migrations through **003** `watch_models`).

---

## Before you start

- [ ] Unraid **Docker** enabled (**Settings → Docker**).
- [ ] **Terminal** access (**Main → Terminal** or SSH as `root`) for one network command and optional `mkdir`.
- [ ] Your Unraid **LAN IP** (for opening the web UI), e.g. from **Main** or **Settings → Network Settings**.
- [ ] A GitHub repo whose **Actions** workflow publishes **`ghcr.io/<your-username>/watchfinder`** (see **`.github/workflows/docker-publish.yml`**). If the package is **private**, create a GitHub **PAT** with **`read:packages`** and add **`ghcr.io`** credentials on Unraid before pulling.
- [ ] **eBay Developers Program** — [developer.ebay.com](https://developer.ebay.com): register with your eBay account and wait for any required **authorization / verification** eBay applies to new developer access. **Production Browse API** credentials may be unavailable until that completes. You can still install Postgres and WatchFinder and use the **web UI**; **ingest** needs real **`EBAY_CLIENT_ID`** / **`EBAY_CLIENT_SECRET`** and Browse access (see root **`README.md` → eBay**).

---

## 1. Folders

Paths live on the Unraid server (the array), not on your Windows PC.

**Easiest — Terminal:**

```bash
mkdir -p /mnt/user/appdata/watchfinder/{logs,data,imports}
mkdir -p /mnt/user/appdata/postgres-watchfinder
```

**Or** under the **`appdata`** share (Windows / file manager): create **`watchfinder`**, **`watchfinder/logs`**, **`watchfinder/data`**, **`watchfinder/imports`**, and **`postgres-watchfinder`** beside **`watchfinder`**.

| Host path | Container (WatchFinder) | Purpose |
|-----------|-------------------------|---------|
| `/mnt/user/appdata/watchfinder` | `/app/config` | Config |
| `/mnt/user/appdata/watchfinder/logs` | `/app/logs` | Logs |
| `/mnt/user/appdata/watchfinder/data` | `/app/data` | App data / cache |
| `/mnt/user/appdata/watchfinder/imports` | `/imports` | Optional manual file drops |
| `/mnt/user/appdata/postgres-watchfinder` | `/var/lib/postgresql/data` (Postgres only) | Database — **back this up** |

---

## 2. Docker network

So the app can reach Postgres by name **`watchfinder-postgres`**, both containers must share a **user-defined** network (the default bridge often does not resolve container names).

**Once, in Terminal:**

```bash
docker network create watchfinder-net
```

Check: `docker network ls` → you should see **`watchfinder-net`**.

Attach **both** containers to this network (Unraid **Docker → Add/Edit Container → Advanced**: **Network type** `watchfinder-net`, or **Extra Parameters:** `--network=watchfinder-net` — wording varies by Unraid version; avoid duplicate `--network` flags).

---

## 3. PostgreSQL

Use the **official** image; do not rely on random Community Applications templates matching **`postgres:16`**.

**Docker → Add Container**

| Field | Value |
|--------|--------|
| **Name** | `watchfinder-postgres` |
| **Repository** | `postgres:16` |

**Variables**

| Key | Value |
|-----|--------|
| `POSTGRES_DB` | `watchfinder` |
| `POSTGRES_USER` | `watchfinder` |
| `POSTGRES_PASSWORD` | *(strong password; must match the password inside the app’s `DATABASE_URL`)* |
| `TZ` | e.g. `Europe/London` |

**Path**

| Container path | Host path |
|----------------|-----------|
| `/var/lib/postgresql/data` | `/mnt/user/appdata/postgres-watchfinder` |

**Network:** `watchfinder-net` (see §2).

**Port 5432:** leave **unmapped** if only WatchFinder talks to Postgres (recommended). Map host→5432 only if you need external tools (use a strong password; mind exposure).

Start the container; first boot may take a minute.

---

## 4. WatchFinder app (after GHCR has your image)

**Repository example:** `ghcr.io/yourgithubuser/watchfinder:latest` — use **lowercase** if GHCR rejects mixed case.

A full list of path and variable fields (copy-paste friendly) is in **`deploy/unraid/watchfinder.xml`** in the repo — replace **`YOUR_GITHUB_USERNAME`** everywhere.

**Docker → Add Container**

| Field | Value |
|--------|--------|
| **Name** | `watchfinder` (or any name you prefer) |
| **Repository** | your GHCR image, e.g. `ghcr.io/yourgithubuser/watchfinder:latest` |

**Port:** container **8080** → host **8080** (or another free host port).

**Paths**

| Container | Host |
|-----------|------|
| `/app/config` | `/mnt/user/appdata/watchfinder` |
| `/app/logs` | `/mnt/user/appdata/watchfinder/logs` |
| `/app/data` | `/mnt/user/appdata/watchfinder/data` |
| `/imports` | `/mnt/user/appdata/watchfinder/imports` |

**Network:** `watchfinder-net` (same as Postgres).

**Variables (minimum)**

| Key | Example / note |
|-----|----------------|
| `DATABASE_URL` | `postgresql+psycopg://watchfinder:YOUR_PASSWORD@watchfinder-postgres:5432/watchfinder` |
| `EBAY_CLIENT_ID` | from eBay developer portal (after your dev account is authorized) |
| `EBAY_CLIENT_SECRET` | from eBay developer portal (same) |
| `EBAY_ENVIRONMENT` | `production` (or `sandbox` while testing) |
| `TZ` | e.g. `Europe/London` |

**Often set (see XML template for defaults)**

| Key | Purpose |
|-----|---------|
| `EBAY_MARKETPLACE_ID` | e.g. `EBAY_GB`, `EBAY_US` |
| `EBAY_SEARCH_QUERY` | Browse search string (default e.g. `wristwatch`) |
| `EBAY_SEARCH_LIMIT` | Items per scheduled run (1–200) |
| `INGEST_INTERVAL_MINUTES` | Minutes between runs (5–1440) |
| `APP_PORT` | Must match container listen port (usually **8080**) |
| `LOG_LEVEL` | e.g. `INFO` |
| `EBAY_CATEGORY_TREE_ID` | Optional; taxonomy advanced use |

**Start order:** Postgres first, then WatchFinder.

**Browser**

- **Web UI:** `http://YOUR_UNRAID_IP:HOST_PORT/` (e.g. `:8080`)
- **Settings (ingest queries, interval, “Ingest now”):** `http://YOUR_UNRAID_IP:HOST_PORT/settings/`
- **Listing detail (valuation edits, internal comps):** open any listing → detail URL; first deploy after **DB migration 002** is applied automatically on container start (`alembic upgrade head` in the image entrypoint).
- **API docs:** `http://YOUR_UNRAID_IP:HOST_PORT/docs`
- **Health:** `http://YOUR_UNRAID_IP:HOST_PORT/health` (used by the image healthcheck)

**Connection tips**

- Hostname **`watchfinder-postgres`** works only if **both** containers use **`watchfinder-net`**.
- Special characters in the DB password must be **URL-encoded** inside `DATABASE_URL`; simplest first-time password: **letters and numbers only**.

---

## 5. GitHub and GHCR (short)

1. Repository contains **`.github/workflows/docker-publish.yml`**, which builds and pushes to **GHCR**.
2. Push **`main`**; confirm the **`watchfinder`** package under the repository **Packages**.
3. Use that **exact** image name in Unraid’s **Repository** field. Unraid **pulls** the image; it does not build from source on the server.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| App cannot connect to DB | Both on `watchfinder-net`; Postgres container name **`watchfinder-postgres`**; password matches **`DATABASE_URL`**; Postgres running. |
| DNS / no route | Recreate `watchfinder-net`, re-attach both containers, restart. |
| Port in use | Change **host** port mapping; open the UI with that port; set **`APP_PORT`** to match the **container** port if you change it. |
| Postgres fails | **Docker** logs for `watchfinder-postgres`. |
| Cannot pull image | Private package: PAT + Unraid registry login for **`ghcr.io`**. |
| Ingest fails / token errors | eBay dev account still pending approval, wrong **production vs sandbox** keys, missing **Browse** API access, or bad **`EBAY_MARKETPLACE_ID`**. Check **WatchFinder** Docker logs after a scheduled run; update env and restart when eBay has issued credentials. |

---

## Changing or extending the app

The canonical feature and deployment spec lives in **`CURSOR_PROMPT.txt`**. The implemented codebase is described in **`PROGRESS.md`** at the repository root.
