"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { fetchJson } from "@/lib/api";
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

const CANDIDATES_PAGE_SIZE_KEY = "watchfinder-candidates-page-size";
const CANDIDATES_PAGE_SIZE_OPTIONS = [30, 50, 100, 200] as const;

export default function CandidatesPage() {
  const [filters, setFilters] = useState({
    title_q: "",
    brand: "",
    price_max: "",
    repair_keyword: "",
    confidence_min: "",
    sale_type: "",
    ending_within_hours: "",
    listing_active: "active" as "active" | "inactive" | "all",
    exclude_quartz: false,
  });
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState<number>(() => {
    if (typeof window === "undefined") return 30;
    const raw = Number(localStorage.getItem(CANDIDATES_PAGE_SIZE_KEY));
    return CANDIDATES_PAGE_SIZE_OPTIONS.includes(
      raw as (typeof CANDIDATES_PAGE_SIZE_OPTIONS)[number],
    )
      ? raw
      : 30;
  });
  const [queryNonce, setQueryNonce] = useState(0);
  const [sortBy, setSortBy] = useState("last_seen");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [data, setData] = useState<ListingListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [warn, setWarn] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
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
    if (f.price_max) q.set("price_max", f.price_max);
    if (f.repair_keyword) q.set("repair_keyword", f.repair_keyword);
    if (f.confidence_min) q.set("confidence_min", f.confidence_min);
    if (f.sale_type) q.set("sale_type", f.sale_type);
    if (f.ending_within_hours) q.set("ending_within_hours", f.ending_within_hours);
    q.set("listing_active", f.listing_active);
    if (f.exclude_quartz) q.set("exclude_quartz", "true");
    q.set("sort_by", sortBy);
    q.set("sort_dir", sortDir);
    const qs = q.toString();

    setWarn(null);
    fetchJson<ListingListResponse>(`/api/candidates?${qs}`)
      .then(setData)
      .catch(async () => {
        // Compatibility fallback: if /api/candidates is unavailable, use /api/listings with profit floor.
        const q2 = new URLSearchParams(qs);
        if (!q2.get("profit_min")) q2.set("profit_min", "0.01");
        const fallback = await fetchJson<ListingListResponse>(`/api/listings?${q2.toString()}`);
        setWarn("Using fallback query via /api/listings (candidate endpoint unavailable).");
        setData(fallback);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [skip, limit, sortBy, sortDir]);

  useEffect(() => {
    try {
      localStorage.setItem(CANDIDATES_PAGE_SIZE_KEY, String(limit));
    } catch {
      // Ignore storage write errors.
    }
    setSkip(0);
  }, [limit]);

  useEffect(() => {
    void load();
  }, [skip, queryNonce, load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Repair candidates</h1>
        <p className="mt-1 text-muted-foreground">
          Listings where <strong>potential profit</strong> is positive after estimated repair. When a row is
          linked to the <strong>watch database</strong> and that catalog entry has manual or observed{" "}
          <strong>£</strong> bounds, resale is anchored to that <strong>working-market</strong> value (manual /
          WatchBase import preferred over observed asks). The ask is converted with Frankfurter{" "}
          <strong>→ GBP</strong> when needed, then profit is shown in the <strong>listing’s currency</strong>.
          Otherwise the old <strong>list price × multiplier</strong> heuristic applies. Not professional
          appraisal — see each listing’s score explanations.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Optional refinements, then Apply. <strong>Price max</strong> is a plain numeric filter (no currency
            conversion).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Title contains</label>
              <Input
                value={filters.title_q}
                onChange={(e) => setFilters((f) => ({ ...f, title_q: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Brand</label>
              <Input
                value={filters.brand}
                onChange={(e) => setFilters((f) => ({ ...f, brand: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Price max (numeric)</label>
              <Input
                value={filters.price_max}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, price_max: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Repair keyword</label>
              <Input
                value={filters.repair_keyword}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, repair_keyword: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Confidence min</label>
              <Input
                value={filters.confidence_min}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, confidence_min: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Sale type</label>
              <Input
                value={filters.sale_type}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, sale_type: e.target.value }))
                }
                placeholder="AUCTION / FIXED_PRICE / BEST_OFFER"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Ending within hours</label>
              <Input
                value={filters.ending_within_hours}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, ending_within_hours: e.target.value }))
                }
                placeholder="24"
              />
            </div>
            <Button
              type="button"
              onClick={() => {
                setSkip(0);
                setQueryNonce((n) => n + 1);
              }}
            >
              Apply
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Listing status</label>
              <select
                className="flex h-9 rounded-md border border-border bg-background px-2 text-sm"
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
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border"
                checked={filters.exclude_quartz}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, exclude_quartz: e.target.checked }))
                }
              />
              Exclude quartz
            </label>
          </div>
        </CardContent>
      </Card>

      {err && (
        <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-200">
          {err}
        </div>
      )}
      {warn && !err && (
        <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-4 text-sm text-amber-100">
          {warn}
        </div>
      )}

      {loading && !data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : data ? (
        <>
          <p className="text-sm text-muted-foreground">
            {data.total} candidate(s) · skip {data.skip} · limit {data.limit}
          </p>
          <div className="flex items-center gap-2">
            <label
              htmlFor="candidates-page-size"
              className="text-xs font-medium text-muted-foreground"
            >
              Rows per page
            </label>
            <select
              id="candidates-page-size"
              className="h-9 rounded-md border border-input bg-background px-2 text-sm text-foreground"
              value={String(limit)}
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              {CANDIDATES_PAGE_SIZE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
          <CandidatesTable
            rows={data.items}
            sortBy={sortBy}
            sortDir={sortDir}
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

function CandidatesTable({
  rows,
  sortBy,
  sortDir,
  onSort,
}: {
  rows: ListingSummary[];
  sortBy: string;
  sortDir: SortDir;
  onSort: (column: string) => void;
}) {
  if (!rows.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No candidates yet — ingest listings with repair-related keywords or tune scoring.
      </p>
    );
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
            title="eBay asking price in that listing’s currency."
          />
          <SortableTableHead
            label="Profit"
            column="profit"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
            title="Potential profit in the listing’s currency (catalog working value − rule repair − ask, or heuristic)."
          />
          <TableHead className="text-muted-foreground w-28">Catalog</TableHead>
          <SortableTableHead
            label="Confidence"
            column="confidence"
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
          <TableHead className="text-muted-foreground">Sale type</TableHead>
          <TableHead className="text-muted-foreground">Ends</TableHead>
          <TableHead className="text-muted-foreground">eBay</TableHead>
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
              <Badge variant="success">
                {money(r.score?.potential_profit, r.currency)}
              </Badge>
            </TableCell>
            <TableCell className="text-xs">
              {r.watch_model_id ? (
                <Link
                  href={`/watch-models/detail/?id=${r.watch_model_id}`}
                  className="text-primary underline-offset-2 hover:underline"
                >
                  Linked
                </Link>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell>
              {r.score?.confidence != null
                ? `${(Number(r.score.confidence) * 100).toFixed(0)}%`
                : "—"}
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
            <TableCell className="align-top">
              {r.web_url ? (
                <Button variant="outline" size="sm" asChild>
                  <a href={r.web_url} target="_blank" rel="noopener noreferrer">
                    View
                  </a>
                </Button>
              ) : (
                <span className="text-xs text-muted-foreground">—</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
