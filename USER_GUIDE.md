# WatchFinder user guide

This guide is for **day-to-day use**: pulling eBay listings into your database, working with brands/calibers, clearing the **match queue**, and spotting listings worth buying. Technical setup (Docker, env vars, Unraid) stays in [`README.md`](README.md) and [`Kickoff Documents/SIMPLIFIED_NOVICE_SETUP.md`](Kickoff%20Documents/SIMPLIFIED_NOVICE_SETUP.md).

---

## What you see in the app

The top navigation matches how most people work:

| Page | Use it to… |
|------|------------|
| **Dashboard** | See totals, eBay API usage counters, and recent listings at a glance. |
| **Listings** | Browse everything you have ingested, filter heavily, open detail. |
| **Candidates** | See listings where **potential profit** is **positive** (rule-based repair vs ask). |
| **Watch database** | Maintain canonical watch rows (brand, reference, prices in £, caliber text, links to listings). |
| **Match queue** | Resolve listings that need a **manual** link to the watch database (when you use review mode). |
| **Not interested** | Manage blocked eBay item IDs so ingest does not pull them back. |
| **Settings** | Browse search lines, ingest timing, stale refresh, match-queue behavior, exclusions. |

---

## Getting watch listings into WatchFinder

1. **Configure eBay access** in **Settings** (Browse API credentials and OAuth behave as documented in [`README.md`](README.md)). Without valid credentials, ingest cannot fetch live results.

2. **Define what eBay searches** using the **Browse search lines** (and related limits: items per line, pages, interval). These are the queries WatchFinder runs on a schedule.

3. **Run ingest**  
   - Wait for the **scheduled** ingest, or  
   - Use **Ingest now** on **Settings** to queue a full cycle in the background (check server logs if something looks stuck).

4. **Confirm rows appear** on **Dashboard** (recent listings) or **Listings** (full table). New items are analyzed: titles are parsed, repair signals may attach, and opportunity scores may be computed when repair signals exist.

5. **Refresh stale prices** (optional): **Stale refresh now** or the stale-refresh scheduler in **Settings** updates older active listings via eBay. For a full pass over active listings, use **Refresh ALL active now** when you need everything current.

**Tip:** **Listings** defaults to **active** items only. Use the **listing active** filter if you need ended listings too.

---

## Brands, calibers, and filtering

- **Parsed text** comes from titles/descriptions (brand, reference hints, caliber hints, condition, etc.).

- **Resolved entities** (brands, stock references, **calibers**) are dictionary rows in Postgres. They fill in as listings are processed and when you use **entity backfill** from the API (see [`README.md`](README.md) — `POST` routes under watch models / entities).

- **On the Listings page**, you can filter by:
  - **Brand**, **Title contains**, **Contains text (any field)** (broad search across many stored fields),
  - **Listing type**: Watch / Movement / Other parts / Unknown,
  - **Caliber known** (yes/no),
  - **Caliber id (UUID)** — narrows to listings **linked** to that caliber row.

**Finding a caliber UUID:** Open **Swagger** at `/docs` on your server, call **`GET /api/entities/calibers`** (with optional `q`), and copy the `id` you need. Paste that UUID into **Caliber id** on **Listings** (or use the same query parameter in the API). There is no separate “calibers browser” page in the UI today; Swagger is the straightforward way to look up IDs.

**Watch database** rows also carry a **caliber** text field and power **Donor movement market** stats on model detail for **movement** listings linked to a resolved caliber — useful when pricing donor movements.

---

## Match queue: what it is and how to “clear” it

The **match queue** appears only when **Settings → Watch catalog matching** is set to **Review queue** (not **Automatic**). In that mode, listings that are not clearly auto-matchable are queued for you to **link to an existing watch row**, **create** a new catalog row, or **dismiss**.

### Ways the queue becomes empty (“cleared”)

1. **Work each item**  
   Open **Match queue** → **Review** on a row → on the detail page choose **Match** (pick a watch database row), **Create new**, or **Dismiss**. Any of these **removes that item** from the queue.

2. **Not interested**  
   From the queue list, **Not interested** removes the listing **and** blocks that eBay item ID (same idea as on listing detail). It clears the row from the queue but **stops future ingest** for that item until you change **Not interested** settings.

3. **Automatic mode**  
   Switching to **Automatic** stops **new** items from entering the queue; existing queue rows stay until you resolve them.

4. **Nothing pending**  
   When there are no rows, the page shows **All clear** — that is the normal “empty queue” state.

### Keep the queue moving

- **Sync unmatched listings** (on the Match queue page) re-runs matching for **active** listings with **no** watch-database link — same idea as the optional **scheduled match queue sync** in **Settings** (set interval minutes; **0** turns the scheduler off).

- **Require identity** (toggle on Match queue): when **on**, only listings with parsed **brand** and **(reference or model family)** are queued in review mode. Turn **off** if you want more borderline titles to appear for manual review.

---

## Finding a good deal to buy

WatchFinder does **not** predict sold prices from eBay history. It combines **your** catalog bounds, **asking** prices in your DB, and **rule-based** repair estimates. Treat numbers as **hints**, not guarantees.

**Practical workflow**

1. **Start at Candidates**  
   This list is restricted to listings with **positive potential profit** after estimated repair. Sort by **potential profit**, **confidence**, or **last seen** depending on whether you want size of edge vs freshness.

2. **Open listing detail**  
   Read **Opportunity score**: **Potential profit**, **Est. resale**, **Est. repair (total)**, **Max buy (rule)**, **Confidence**, **Risk**, and the **explanations** (how the score was built).  
   - If the listing is linked to a **watch database** row with **manual or observed £ bounds**, resale is anchored more tightly than the generic heuristic.  
   - For **movement** listings, a **Donor movement hint** may show median asking prices for the same caliber (other movement listings); use **Use median as donor cost** if that matches how you buy donors, then **Save changes**.

3. **Improve the catalog**  
   If a listing is **unlinked** or poorly linked, use **Match queue** or **Promote to watch database** / listing overrides so the next **analyze** run can use better resale context.

4. **Filter Listings**  
   Use **Profit min**, **Repair keyword**, **price** caps, **listing type**, and **exclude quartz** to narrow raw inventory before drilling into detail.

5. **Block noise**  
   Use **Not interested** for sellers or items you never want to see again.

**Currency note:** Listings use **each item’s eBay currency**. The watch database stores **£** bounds for many fields; the UI explains mixed displays on **Settings** and several cards. **List / candidate price filters** compare **numeric** amounts as stored — they do **not** auto-convert between currencies.

---

## Quick reference

| Goal | Where to go |
|------|-------------|
| Change what eBay searches | **Settings** → Browse search lines |
| Pull new listings soon | **Settings** → **Ingest now** |
| Browse all inventory | **Listings** |
| See positive-profit rows only | **Candidates** |
| Resolve catalog links | **Match queue** |
| Edit valuation / listing type / watch link | **Listings** → open a row → detail |
| Block an eBay item | Listing detail or Match queue → **Not interested** |
| Look up API fields / caliber list | **`/docs`** (Swagger) |

For every button label and workflow nuance, see [`buttons.md`](buttons.md). For implementation scope and API tables, see [`README.md`](README.md) and [`PROGRESS.md`](PROGRESS.md).
