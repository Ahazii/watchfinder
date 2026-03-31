WATCHFINDER — KICKOFF DOCUMENTS
=================================

This folder holds the original **Unraid runbook** and **Cursor build spec**. The main repo is already implemented; use the root **README.md** and **PROGRESS.md** for day-to-day reference.

FILES
-----
- README_START_HERE.txt — this index
- SIMPLIFIED_NOVICE_SETUP.md — Unraid: folders, Docker network, Postgres, app container, GHCR (step-by-step)
- CURSOR_PROMPT.txt — full product/deploy/scoring spec (reference or paste into Cursor for changes)

MAIN REPO DOCS (project root)
-----------------------------
- README.md — quick start, API, Docker Compose, CI/CD, Unraid summary, env table
- PROGRESS.md — phases 1–4, repo map, backlog
- .env.example — environment variables
- deploy/unraid/watchfinder.xml — Unraid template XML (replace YOUR_GITHUB_USERNAME)

ORDER (if you are deploying from scratch)
-----------------------------------------
1. Push the repo to GitHub; confirm Actions publish **ghcr.io/<owner>/watchfinder** on **main**.
2. On Unraid: follow SIMPLIFIED_NOVICE_SETUP.md (folders, watchfinder-net, postgres:16, then WatchFinder image).
3. Match **POSTGRES_PASSWORD** and **DATABASE_URL**; set eBay variables from the developer portal.

REMINDERS
---------
- GHCR image path: use your GitHub user/org; registry paths are often **lowercase**.
- Unraid pulls the prebuilt image — no on-server **git build** for production.
- Private GHCR: PAT with **read:packages** + registry auth on Unraid.
