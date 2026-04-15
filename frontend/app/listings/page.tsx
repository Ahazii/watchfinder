"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiUrl, fetchJson } from "@/lib/api";
import type { ListingListResponse, ListingSummary } from "@/lib/types";
import { money, dateShort } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  SortableTableHead,
  type SortDir,
} from "@/components/sortable-table-head";
import { ListingThumb } from "@/components/listing-thumb";
import { TableThumbSizeSelect } from "@/components/table-thumb-size-select";
import { TABLE_THUMB_STORAGE, usePersistedTableThumbSize } from "@/lib/table-thumb-sizes";

const LISTINGS_STATE_KEY = "watchfinder-listings-state-v1";
const LISTINGS_PAGE_SIZE_OPTIONS = [30, 50, 100, 200] as const;

type ListingsPageState = {
  filters: {
    title_q: string;
    brand: string;
    price_min: string;
    price_max: string;
    repair_keyword: string;
    condition_q: string;
    movement: string;
    caliber_known: string;
    confidence_min: string;
    profit_min: string;
    sale_type: string;
    ending_within_hours: string;
    listing_active: "active" | "inactive" | "all";
    exclude_quartz: boolean;
  };
  skip: number;
  limit?: number;
  sortBy: string;
  sortDir: SortDir;
};

export default function ListingsPage() {
  const [filters, setFilters] = useState({
    title_q: "",
    brand: "",
    price_min: "",
    price_max: "",
    repair_keyword: "",
    condition_q: "",
    movement: "",
    caliber_known: "",
    confidence_min: "",
    profit_min: "",
    sale_type: "",
    ending_within_hours: "",
    listing_active: "active" as "active" | "inactive" | "all",
    exclude_quartz: false,
  });
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState<number>(30);
  const [queryNonce, setQueryNonce] = useState(0);
  const [sortBy, setSortBy] = useState("last_seen");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [data, setData] = useState<ListingListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [promoteBusyId, setPromoteBusyId] = useState<string | null>(null);
  const [notInterestedBusyId, setNotInterestedBusyId] = useState<string | null>(null);
  const [promoteMsg, setPromoteMsg] = useState<string | null>(null);
  const [recheckBusy, setRecheckBusy] = useState(false);
  const [recheckMsg, setRecheckMsg] = useState<string | null>(null);
  const { sizeId: listingsThumbId, setSizeId: setListingsThumbId, sizeClass: listingsThumbClass } =
    usePersistedTableThumbSize(TABLE_THUMB_STORAGE.listings);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  useEffect(() => {
    try {
      const raw = localStorage.getItem(LISTINGS_STATE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as ListingsPageState;
        if (parsed?.filters) setFilters(parsed.filters);
        if (typeof parsed?.skip === "number" && parsed.skip >= 0) setSkip(parsed.skip);
        if (
          typeof parsed?.limit === "number" &&
          LISTINGS_PAGE_SIZE_OPTIONS.includes(parsed.limit as (typeof LISTINGS_PAGE_SIZE_OPTIONS)[number])
        ) {
          setLimit(parsed.limit);
        }
        if (typeof parsed?.sortBy === "string" && parsed.sortBy) setSortBy(parsed.sortBy);
        if (parsed?.sortDir === "asc" || parsed?.sortDir === "desc") setSortDir(parsed.sortDir);
      }
    } catch {
      // Ignore malformed local state; defaults remain.
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    const state: ListingsPageState = { filters, skip, sortBy, sortDir };
    state.limit = limit;
    localStorage.setItem(LISTINGS_STATE_KEY, JSON.stringify(state));
  }, [ready, filters, skip, sortBy, sortDir, limit]);

  useEffect(() => {
    setSkip(0);
  }, [limit]);

  const load = useCallback(() => {
    setLoading(true);
    setErr(null);
    const f = filtersRef.current;
    const q = new URLSearchParams();
    q.set("skip", String(skip));
    q.set("limit", String(limit));
    if (f.title_q) q.set("title_q", f.title_q);
    if (f.brand) q.set("brand", f.brand);
    if (f.price_min) q.set("price_min", f.price_min);
    if (f.price_max) q.set("price_max", f.price_max);
    if (f.repair_keyword) q.set("repair_keyword", f.repair_keyword);
    if (f.condition_q) q.set("condition_q", f.condition_q);
    if (f.movement) q.set("movement", f.movement);
    if (f.caliber_known === "yes") q.set("caliber_known", "true");
    if (f.caliber_known === "no") q.set("caliber_known", "false");
    if (f.confidence_min) q.set("confidence_min", f.confidence_min);
    if (f.profit_min) q.set("profit_min", f.profit_min);
    if (f.sale_type) q.set("sale_type", f.sale_type);
    if (f.ending_within_hours) q.set("ending_within_hours", f.ending_within_hours);
    q.set("listing_active", f.listing_active);
    if (f.exclude_quartz) q.set("exclude_quartz", "true");
    q.set("sort_by", sortBy);
    q.set("sort_dir", sortDir);

    fetchJson<ListingListResponse>(`/api/listings?${q.toString()}`)
      .then(setData)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [skip, limit, sortBy, sortDir]);

  useEffect(() => {
    if (!ready) return;
    void load();
  }, [skip, queryNonce, load, ready]);

  const promoteToCatalog = (listingId: string) => {
    setPromoteBusyId(listingId);
    setPromoteMsg(null);
    fetch(apiUrl(`/api/listings/${listingId}/promote-watch-catalog`), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        setPromoteMsg("Catalog updated for one listing.");
        setQueryNonce((n) => n + 1);
      })
      .catch((e: Error) => setPromoteMsg(e.message))
      .finally(() => setPromoteBusyId(null));
  };

  const markNotInterested = (listingId: string) => {
    setNotInterestedBusyId(listingId);
    setPromoteMsg(null);
    fetch(apiUrl(`/api/listings/${listingId}/not-interested`), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        setPromoteMsg("Moved one listing to not interested.");
        setQueryNonce((n) => n + 1);
      })
      .catch((e: Error) => setPromoteMsg(e.message))
      .finally(() => setNotInterestedBusyId(null));
  };

  const recheckVisibleActiveStatus = async () => {
    if (!data?.items?.length) return;
    setRecheckBusy(true);
    setRecheckMsg(null);
    let checked = 0;
    let ended = 0;
    let failed = 0;
    for (const row of data.items) {
      try {
        const res = await fetch(apiUrl(`/api/listings/${row.id}/refresh-from-ebay`), {
          method: "POST",
          headers: { Accept: "application/json" },
        });
        if (!res.ok) {
          failed += 1;
          continue;
        }
        const detail = (await res.json()) as { is_active?: boolean };
        checked += 1;
        if (detail.is_active === false) ended += 1;
      } catch {
        failed += 1;
      }
    }
    setRecheckMsg(
      `Rechecked ${checked} row(s) on this page: ${ended} inactive, ${failed} failed.`,
    );
    setQueryNonce((n) => n + 1);
    setRecheckBusy(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Listings</h1>
        <p className="mt-1 text-muted-foreground">
          Search ingested eBay items; open a row for full parse, signals, and score explanations.{" "}
          <strong>Price</strong> and <strong>profit</strong> in the table use each row’s eBay currency (symbol
          in the cell). <strong>Price min/max</strong> filters compare raw numbers as stored.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Adjust fields, then Apply. Pagination keeps the same filters. Price and profit filters are plain
            numeric comparisons (they do not convert currencies).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Field
              label="Title contains"
              value={filters.title_q}
              onChange={(v) => setFilters((f) => ({ ...f, title_q: v }))}
            />
            <Field
              label="Brand"
              value={filters.brand}
              onChange={(v) => setFilters((f) => ({ ...f, brand: v }))}
            />
            <Field
              label="Price min (numeric)"
              value={filters.price_min}
              onChange={(v) => setFilters((f) => ({ ...f, price_min: v }))}
            />
            <Field
              label="Price max (numeric)"
              value={filters.price_max}
              onChange={(v) => setFilters((f) => ({ ...f, price_max: v }))}
            />
            <Field
              label="Repair keyword"
              value={filters.repair_keyword}
              onChange={(v) => setFilters((f) => ({ ...f, repair_keyword: v }))}
            />
            <Field
              label="Condition"
              value={filters.condition_q}
              onChange={(v) => setFilters((f) => ({ ...f, condition_q: v }))}
            />
            <Field
              label="Movement"
              value={filters.movement}
              onChange={(v) => setFilters((f) => ({ ...f, movement: v }))}
            />
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Caliber known
              </label>
              <select
                className="flex h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
                value={filters.caliber_known}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, caliber_known: e.target.value }))
                }
              >
                <option value="">Any</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <Field
              label="Confidence min (0–1)"
              value={filters.confidence_min}
              onChange={(v) => setFilters((f) => ({ ...f, confidence_min: v }))}
            />
            <Field
              label="Profit min (numeric)"
              value={filters.profit_min}
              onChange={(v) => setFilters((f) => ({ ...f, profit_min: v }))}
            />
            <Field
              label="Sale type (e.g. AUCTION)"
              value={filters.sale_type}
              onChange={(v) => setFilters((f) => ({ ...f, sale_type: v }))}
            />
            <Field
              label="Ending within hours"
              value={filters.ending_within_hours}
              onChange={(v) => setFilters((f) => ({ ...f, ending_within_hours: v }))}
            />
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Listing status
              </label>
              <select
                className="flex h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
                value={filters.listing_active}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    listing_active: e.target.value as "active" | "inactive" | "all",
                  }))
                }
              >
                <option value="active">Active only</option>
                <option value="inactive">Inactive only</option>
                <option value="all">All</option>
              </select>
            </div>
            <label className="flex cursor-pointer items-center gap-2 pt-6 text-sm sm:col-span-2 lg:col-span-3">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border"
                checked={filters.exclude_quartz}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, exclude_quartz: e.target.checked }))
                }
              />
              <span>Exclude quartz (title or parsed movement)</span>
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={() => {
                setSkip(0);
                setQueryNonce((n) => n + 1);
              }}
            >
              Apply
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setFilters({
                  title_q: "",
                  brand: "",
                  price_min: "",
                  price_max: "",
                  repair_keyword: "",
                  condition_q: "",
                  movement: "",
                  caliber_known: "",
                  confidence_min: "",
                  profit_min: "",
                  sale_type: "",
                  ending_within_hours: "",
                  listing_active: "active",
                  exclude_quartz: false,
                });
                setSkip(0);
                setQueryNonce((n) => n + 1);
              }}
            >
              Clear
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={recheckBusy || !data?.items?.length}
              onClick={() => void recheckVisibleActiveStatus()}
              title='Refresh active status for rows on this page using eBay page marker "We looked everywhere."'
            >
              {recheckBusy ? "Rechecking…" : "Recheck active (this page)"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {err && (
        <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-200">
          {err}
        </div>
      )}

      {loading && !data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : data ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              Showing {data.items.length} of {data.total} (skip {data.skip}, limit{" "}
              {data.limit})
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <label
                  htmlFor="listings-page-size"
                  className="text-xs font-medium text-muted-foreground"
                >
                  Rows per page
                </label>
                <select
                  id="listings-page-size"
                  className="h-9 rounded-md border border-input bg-background px-2 text-sm text-foreground"
                  value={String(limit)}
                  onChange={(e) => setLimit(Number(e.target.value))}
                >
                  {LISTINGS_PAGE_SIZE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
              <TableThumbSizeSelect
                id="listings-thumb-size"
                value={listingsThumbId}
                onChange={setListingsThumbId}
              />
            </div>
          </div>
          {promoteMsg ? (
            <p className="text-sm text-muted-foreground">{promoteMsg}</p>
          ) : null}
          {recheckMsg ? (
            <p className="text-sm text-muted-foreground">{recheckMsg}</p>
          ) : null}
          <div className="overflow-x-auto rounded-lg border border-border">
            <ListingsTable
              rows={data.items}
              sortBy={sortBy}
              sortDir={sortDir}
              promoteBusyId={promoteBusyId}
              notInterestedBusyId={notInterestedBusyId}
              thumbSizeClass={listingsThumbClass}
              onPromoteToCatalog={promoteToCatalog}
              onMarkNotInterested={markNotInterested}
              onSort={(column) => {
                if (sortBy === column) {
                  setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                } else {
                  setSortBy(column);
                  setSortDir(column === "title" ? "asc" : "desc");
                }
                setSkip(0);
              }}
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={skip === 0}
              onClick={() => setSkip((s) => Math.max(0, s - limit))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={skip + limit >= data.total}
              onClick={() => setSkip((s) => s + limit)}
            >
              Next
            </Button>
          </div>
        </>
      ) : null}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function ListingsTable({
  rows,
  sortBy,
  sortDir,
  onSort,
  promoteBusyId,
  notInterestedBusyId,
  thumbSizeClass,
  onPromoteToCatalog,
  onMarkNotInterested,
}: {
  rows: ListingSummary[];
  sortBy: string;
  sortDir: SortDir;
  onSort: (column: string) => void;
  promoteBusyId: string | null;
  notInterestedBusyId: string | null;
  thumbSizeClass: string;
  onPromoteToCatalog: (listingId: string) => void;
  onMarkNotInterested: (listingId: string) => void;
}) {
  if (!rows.length) {
    return <p className="text-sm text-muted-foreground">No rows.</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="min-w-[3rem] text-muted-foreground">Photo</TableHead>
          <TableHead className="w-24 text-muted-foreground">Status</TableHead>
          <SortableTableHead
            label="Title"
            column="title"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
          />
          <SortableTableHead
            label="Price"
            column="price"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
            title="Current asking price from eBay, formatted in that listing’s currency (£, $, €, …)."
          />
          <SortableTableHead
            label="Confidence"
            column="confidence"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
          />
          <SortableTableHead
            label="Profit est."
            column="profit"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
            title="Rule-based potential profit in the same currency as the listing’s price."
          />
          <SortableTableHead
            label="Seen"
            column="last_seen"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
          />
          <TableHead className="text-muted-foreground">Sale type</TableHead>
          <TableHead className="text-muted-foreground" title="eBay item end date/time">
            Ends
          </TableHead>
          <TableHead className="w-[1%] whitespace-nowrap text-right text-muted-foreground">
            eBay
          </TableHead>
          <TableHead
            className="w-[1%] whitespace-nowrap text-right text-muted-foreground"
            title="Linked to a row in the watch database (catalog), or add one from this listing."
          >
            Watch DB
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.id}>
            <TableCell className="align-top">
              <ListingThumb urls={r.image_urls} alt="" sizeClass={thumbSizeClass} />
            </TableCell>
            <TableCell className="align-top">
              {r.is_active === false ? (
                <Badge variant="secondary" className="whitespace-nowrap text-amber-200/90">
                  Inactive
                </Badge>
              ) : (
                <Badge variant="outline" className="whitespace-nowrap text-emerald-200/80">
                  Active
                </Badge>
              )}
            </TableCell>
            <TableCell className="max-w-xs">
              <Link
                href={`/listings/detail/?id=${r.id}`}
                className="line-clamp-2 text-primary hover:underline"
              >
                {r.title || r.ebay_item_id}
              </Link>
            </TableCell>
            <TableCell>{money(r.current_price, r.currency)}</TableCell>
            <TableCell>
              {r.score?.confidence != null ? pct(r.score.confidence) : "—"}
            </TableCell>
            <TableCell>
              {r.score?.potential_profit != null ? (
                <Badge
                  variant={
                    Number(r.score.potential_profit) > 0 ? "success" : "secondary"
                  }
                >
                  {money(r.score.potential_profit, r.currency)}
                </Badge>
              ) : (
                "—"
              )}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {dateShort(r.last_seen_at)}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {r.buying_options?.length ? r.buying_options.join(", ") : "—"}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {dateShort(r.listing_ended_at)}
            </TableCell>
            <TableCell className="text-right align-top">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!r.web_url}
                asChild={Boolean(r.web_url)}
              >
                {r.web_url ? (
                  <a href={r.web_url} target="_blank" rel="noopener noreferrer">
                    View
                  </a>
                ) : (
                  <span>View</span>
                )}
              </Button>
            </TableCell>
            <TableCell className="text-right align-top">
              <div className="flex flex-col items-end gap-2">
                {r.watch_model_id ? (
                  <Link
                    href={`/watch-models/detail/?id=${r.watch_model_id}`}
                    className="inline-block text-sm font-medium text-primary hover:underline"
                    title="Open linked watch database entry"
                  >
                    In watch DB
                  </Link>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={promoteBusyId === r.id}
                    title="Save to watch database — create or link a catalog row from this listing"
                    onClick={() => onPromoteToCatalog(r.id)}
                  >
                    {promoteBusyId === r.id ? "…" : "Add to DB"}
                  </Button>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={notInterestedBusyId === r.id}
                  onClick={() => onMarkNotInterested(r.id)}
                  title="Remove this listing and block the eBay item id from future ingest"
                >
                  {notInterestedBusyId === r.id ? "…" : "Not interested"}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function pct(value: string | number) {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(0)}%`;
}
