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
    listing_active: "active" as "active" | "inactive" | "all",
    exclude_quartz: false,
  });
  const [skip, setSkip] = useState(0);
  const [queryNonce, setQueryNonce] = useState(0);
  const [sortBy, setSortBy] = useState("last_seen");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const limit = 30;
  const [data, setData] = useState<ListingListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [promoteBusyId, setPromoteBusyId] = useState<string | null>(null);
  const [promoteMsg, setPromoteMsg] = useState<string | null>(null);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

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
    void load();
  }, [skip, queryNonce, load]);

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Listings</h1>
        <p className="mt-1 text-muted-foreground">
          Search ingested eBay items; open a row for full parse, signals, and score
          explanations.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Adjust fields, then Apply. Pagination keeps the same filters.
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
              label="Price min"
              value={filters.price_min}
              onChange={(v) => setFilters((f) => ({ ...f, price_min: v }))}
            />
            <Field
              label="Price max"
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
              label="Profit min"
              value={filters.profit_min}
              onChange={(v) => setFilters((f) => ({ ...f, profit_min: v }))}
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
                  listing_active: "active",
                  exclude_quartz: false,
                });
                setSkip(0);
                setQueryNonce((n) => n + 1);
              }}
            >
              Clear
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
          <p className="text-sm text-muted-foreground">
            Showing {data.items.length} of {data.total} (skip {data.skip}, limit{" "}
            {data.limit})
          </p>
          {promoteMsg ? (
            <p className="text-sm text-muted-foreground">{promoteMsg}</p>
          ) : null}
          <ListingsTable
            rows={data.items}
            sortBy={sortBy}
            sortDir={sortDir}
            promoteBusyId={promoteBusyId}
            onPromoteToCatalog={promoteToCatalog}
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
  onPromoteToCatalog,
}: {
  rows: ListingSummary[];
  sortBy: string;
  sortDir: SortDir;
  onSort: (column: string) => void;
  promoteBusyId: string | null;
  onPromoteToCatalog: (listingId: string) => void;
}) {
  if (!rows.length) {
    return <p className="text-sm text-muted-foreground">No rows.</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-14 text-muted-foreground">Photo</TableHead>
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
          />
          <SortableTableHead
            label="Seen"
            column="last_seen"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
          />
          <TableHead className="w-[1%] whitespace-nowrap text-right text-muted-foreground">
            Watch DB
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.id}>
            <TableCell className="align-top">
              <ListingThumb urls={r.image_urls} alt="" />
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
            <TableCell className="text-right">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={promoteBusyId === r.id}
                title="Save to watch database — create or link a catalog row from this listing"
                onClick={() => onPromoteToCatalog(r.id)}
              >
                {promoteBusyId === r.id ? "…" : "Add"}
              </Button>
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
