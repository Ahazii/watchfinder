# WatchFinder Button Reference

This document lists the user-facing buttons in the application and what each button does.

Scope notes:
- Covers clickable controls implemented as the shared `Button` component and explicit `<button>` elements in the frontend.
- Excludes plain text links and checkbox/radio inputs unless they are rendered as button-like actions.
- Labels shown below are the visible button text in the UI (or equivalent busy-state text).

## Global Navigation

Primary navigation is in the top nav links (`Dashboard`, `Listings`, `Candidates`, `Watch database`, `Match queue`, `Not interested`, `Settings`), implemented as links rather than buttons.

---

## Dashboard (`/`)

No action buttons on this page.

---

## Listings (`/listings`)

### Filters card
- `Apply`: runs the listing query with current filters and resets pagination to page 1.
- `Clear`: resets all listing filters to defaults and reloads.
- `Recheck active (this page)` / `Rechecking…`: calls live eBay refresh on visible rows to update active/inactive status.

### Table row actions
- `View`: opens listing on eBay in a new tab.
- `Add to DB` / `…`: creates or links a watch database model from this listing.
- `Not interested` / `…`: moves listing to blocklist and removes it from ingest flow.
- `In watch DB` is shown as a link (not a button) when already linked.

### Pagination
- `Previous`: goes to previous page of listings.
- `Next`: goes to next page of listings.

---

## Listing Detail (`/listings/detail`)

### Top actions
- `← Listings`: returns to listings page.
- `View on eBay`: opens eBay listing page.
- `Refresh from eBay` / `Refreshing…`: pulls latest listing payload from eBay and re-evaluates active status.
- `Not interested` / `Working…`: blocks this eBay item ID and redirects to Not Interested page filtered to it.

### Catalog workflow
- `Open in match queue`: opens pending match-queue decision (shown only when review is pending).
- `Save to watch database` / `Working…`: triggers promote/link/create catalog action for this listing.

### Form actions
- `Save changes` / `Saving…`: saves manual valuation and field overrides.

### Error fallback
- `Back to listings`: visible on error state.

---

## Candidates (`/candidates`)

### Filters
- `Apply`: runs candidate query with current filters and resets to page 1.

### Table row actions
- `View`: opens listing on eBay in a new tab.

### Pagination
- `Previous`: previous candidates page.
- `Next`: next candidates page.

---

## Watch Database List (`/watch-models`)

### Header
- `Add model`: opens empty watch model detail form to create a new model.

### Supervised WatchBase import (batch card)
- `Select all on page`: selects all models on the currently visible table page.
- `Select none`: clears current selection.
- `Select unmatched (catalog)` / `Loading…`: replaces selection with models matching unmatched import status.
- `Select without pricing (catalog)` / `Loading…`: replaces selection with models missing pricing coverage.
- `Start supervised import…`: opens the batch import wizard for selected rows.
- `Delete selected (N)` / `Deleting…`: deletes selected catalog rows after confirmation.

### Backfill card
- `Run backfill now` / `Running…`: scans active listings and auto-links/creates catalog rows.

### Table row action
- `Details`: opens model detail page.

### Pagination
- `Previous`: previous watch-models page.
- `Next`: next watch-models page.

---

## Watch Database Detail (`/watch-models/detail`)

### Modal: Find watch (WatchBase/Everywatch/Chrono24)
- `Search markets` / `Searching…`: runs unified market search.
- `Open Google (site:watchbase.com)`: opens external Google site search.
- `Copy URL`: copies candidate URL to clipboard.
- `Use in form`: puts selected URL into modal import URL field.
- `Open Chrono24 search`: opens Chrono24 search URL.
- `Google site:chrono24.co.uk`: opens Google Chrono24 site search.
- `Open detail page`: opens parsed detail result URL.
- `Cancel`: closes modal.
- `Confirm import` / `Importing…`: runs WatchBase import with selected/pasted WatchBase URL.

### Page-level actions
- `← Watch database`: back to model list.
- `Everywatch import tester`: opens dedicated Everywatch debug page.
- `Refresh market snapshots` / `Refreshing…`: refreshes Everywatch/Chrono24 snapshots and optional manual-bound seeding.
- `Import from WatchBase` / `Importing…`: imports from saved/guessed WatchBase reference.
- `Refresh data from WatchBase` / `Refreshing…`: same API import path used for refresh semantics.
- `Find on markets…`: opens draggable find/import modal.
- `Open WatchBase (guess)`: opens guessed WatchBase URL from brand/family/reference.
- `Search WatchBase (Google)`: opens Google search for likely WatchBase page.
- `Open saved reference URL`: opens current saved reference URL.
- `Open saved Everywatch URL`: opens current saved Everywatch URL.
- `Save` / `Saving…`: saves model details.
- `Delete` / `Deleting…`: deletes model after confirmation.

### Error fallback
- `Back to watch database`: visible if load fails.

---

## Everywatch Import Tester (`/watch-models/everywatch-test`)

### Helper actions
- `Open Everywatch search`: opens Everywatch search in new tab using first query line.

### Request actions
- `Run debug fetch` / `Fetching…`: executes debug request set and parser analysis.
- `Refresh market snapshots now` / `Refreshing snapshots…`: triggers snapshot refresh API for entered model ID.

### Per-result actions
- `Copy URL`: copies parsed hit URL.
- `Use in form`: appends selected URL into extra URL textarea.
- `Open detail page`: opens parsed detail result page.
- `Show technical JSON` / `Hide technical JSON`: toggles raw parse JSON visibility.

### Footer links
- `← Watch database`: return to list.
- `Model detail`: opens model detail for current model ID (if provided).

---

## Match Queue (`/watch-review`)

### Header actions
- `Require identity: ON/OFF` / `Saving…`: toggles queue identity requirement setting.
- `Sync unmatched listings` / `Syncing…`: processes unmatched active listings through matching/queueing flow.
- `Refresh`: reloads queue list.

### Queue row actions
- `Show more` / `Show less`: expands/collapses title/description preview.
- `Open eBay (new window)`: opens eBay listing.
- `Review`: opens review-detail decision page.
- `Open in WatchFinder`: opens listing detail page.
- `Not interested` / `…`: blocks listing and removes from queue.

### Picture-size control
- `Small` / `Medium` / `Large` options are in a select (not buttons).

---

## Match Queue Detail (`/watch-review/detail`)

### Header / listing actions
- `← Match queue`: return to queue list.
- `Open on eBay (new window)`: opens eBay listing.
- `Open in WatchFinder`: opens listing detail.
- `Not interested` / `…`: blocks and redirects to Not Interested page.

### Watch database search card
- `Search` / `Searching…`: searches watch database by brand/reference/family/name.
- `Open watch database (new window)`: opens full database list page.
- `Match to this type` / `…`: resolves review by linking listing to selected database model.

### Candidate matches card
- `Match to this` / `…`: resolves review by linking to shown candidate.

### Resolution actions
- `Create new catalog row from listing` / `…`: resolves by creating a new catalog row.
- `Dismiss (no catalogue link)` / `…`: resolves without link.

### Error fallback
- `Back to queue`: visible if load fails.

---

## Not Interested (`/not-interested`)

### Filters
- `Refresh`: reloads blocklist table with current query/filter.

### Row actions
- `I am interested` / `…`: restores row from active blocklist.
- `Delete record`: permanently deletes blocklist history row.

---

## Settings (`/settings`)

### Everywatch credentials card
- `Remove saved password` / `…`: clears stored Everywatch password only.

### Browse search lines card
- `Remove`: removes one search-line row.
- `Add search line`: appends a new empty search-line row.

### Save & manual jobs card
- `Save settings` / `Saving…`: writes settings form to backend.
- `Ingest now`: starts background ingest cycle.
- `Stale refresh now`: runs one stale-listing getItem batch.
- `Check Active (All)` / `Checking…`: recomputes `is_active` for all listings from stored end dates only (no eBay calls).
- `Refresh ALL active now` / `Active refresh running…`: live eBay checks for currently active listings with progress tracking.

---

## Shared Modal: WatchBase Batch Wizard (`WatchbaseBatchWizard`)

Used from watch database list when starting supervised import.

### Header
- `Close`: exits wizard.

### Per-model actions
- `Delete this catalog entry` / `Deleting…`: deletes current model and removes it from queue.
- `Yes — import using saved Reference URL` / `Importing…`: imports from model’s saved reference URL.
- `Yes — import this WatchBase page` / `Importing…`: imports from selected auto result.
- `Search markets` / `Searching…`: manual market search.
- `Open Google (site:watchbase.com)`: external search helper.
- `Import this result` / `Importing…`: imports from selected manual WatchBase hit.
- `Open Chrono24` / `Google Chrono24`: external Chrono24 helpers.
- `Import from pasted URL` / `Importing…`: imports from manually pasted WatchBase URL.
- `No match — skip this watch`: advances wizard without import.

---

## Notes for Maintainers

- Busy-state labels are intentionally listed to make QA validation easier.
- If you add/rename a button, update this file in the same PR.
