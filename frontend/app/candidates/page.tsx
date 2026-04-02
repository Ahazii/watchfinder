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

export default function CandidatesPage() {
  const [filters, setFilters] = useState({
    brand: "",
    price_max: "",
    repair_keyword: "",
    confidence_min: "",
  });
  const [skip, setSkip] = useState(0);
  const [queryNonce, setQueryNonce] = useState(0);
  const [sortBy, setSortBy] = useState("last_seen");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const limit = 30;
  const [data, setData] = useState<ListingListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
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
    if (f.brand) q.set("brand", f.brand);
    if (f.price_max) q.set("price_max", f.price_max);
    if (f.repair_keyword) q.set("repair_keyword", f.repair_keyword);
    if (f.confidence_min) q.set("confidence_min", f.confidence_min);
    q.set("sort_by", sortBy);
    q.set("sort_dir", sortDir);

    fetchJson<ListingListResponse>(`/api/candidates?${q.toString()}`)
      .then(setData)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [skip, limit, sortBy, sortDir]);

  useEffect(() => {
    void load();
  }, [skip, queryNonce, load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Repair candidates</h1>
        <p className="mt-1 text-muted-foreground">
          Listings where rule-based <strong>potential profit</strong> is positive.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Optional refinements, then Apply.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Brand</label>
            <Input
              value={filters.brand}
              onChange={(e) => setFilters((f) => ({ ...f, brand: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Price max</label>
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
          <Button
            type="button"
            onClick={() => {
              setSkip(0);
              setQueryNonce((n) => n + 1);
            }}
          >
            Apply
          </Button>
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
            {data.total} candidate(s) · skip {data.skip}
          </p>
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
            label="Profit"
            column="profit"
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
            label="Seen"
            column="last_seen"
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
          />
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.id}>
            <TableCell className="align-top">
              <ListingThumb urls={r.image_urls} alt="" />
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
            <TableCell>
              {r.score?.confidence != null
                ? `${(Number(r.score.confidence) * 100).toFixed(0)}%`
                : "—"}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {dateShort(r.last_seen_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
