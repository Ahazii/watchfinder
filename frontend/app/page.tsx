"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchJson } from "@/lib/api";
import type { DashboardStats, ListingSummary } from "@/lib/types";
import { money, dateShort } from "@/lib/format";
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
import { ListingThumb } from "@/components/listing-thumb";

const EBAY_RATE_LIMITS_URL =
  "https://developer.ebay.com/api-docs/static/rest-rate-limiting-API.html";
const EBAY_BROWSE_OVERVIEW_URL =
  "https://developer.ebay.com/api-docs/buy/browse/overview.html";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<DashboardStats>("/api/dashboard")
      .then(setData)
      .catch((e: Error) => setErr(e.message));
  }, []);

  if (err) {
    return (
      <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-red-200">
        <p className="font-medium">Could not load dashboard</p>
        <p className="mt-1 text-sm opacity-90">{err}</p>
        <p className="mt-3 text-sm text-muted-foreground">
          If you use <code className="rounded bg-muted px-1">next dev</code>, set{" "}
          <code className="rounded bg-muted px-1">NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080</code>{" "}
          and run the API on port 8080.
        </p>
      </div>
    );
  }

  if (!data) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const statCards = [
    { label: "Total listings", value: data.total_listings },
    { label: "Active", value: data.active_listings },
    { label: "Candidates (profit > 0)", value: data.candidate_count },
    { label: "With repair signals", value: data.listings_with_repair_signals },
    {
      label: "eBay Browse searches (ingest)",
      value: data.ebay_browse_search_calls ?? 0,
    },
    {
      label: "eBay OAuth token refreshes",
      value: data.ebay_oauth_token_calls ?? 0,
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-muted-foreground">
          Ingested listings, repair signals, and opportunity highlights.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((s) => (
          <Card key={s.label}>
            <CardHeader className="pb-2">
              <CardDescription>{s.label}</CardDescription>
              <CardTitle className="text-3xl tabular-nums">{s.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <p className="text-sm text-muted-foreground">
        Outbound eBay usage is counted per successful ingest call (one{" "}
        <code className="rounded bg-muted px-1">item_summary/search</code> per
        query per cycle, plus an OAuth token request when the cached token
        expires). Official limits and fair-use rules:{" "}
        <a
          href={EBAY_RATE_LIMITS_URL}
          className="text-primary underline-offset-4 hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          REST API rate limiting
        </a>
        {" · "}
        <a
          href={EBAY_BROWSE_OVERVIEW_URL}
          className="text-primary underline-offset-4 hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          Buy Browse API overview
        </a>
        .
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Recent listings</CardTitle>
          <CardDescription>Last five updated from ingest.</CardDescription>
        </CardHeader>
        <CardContent>
          <RecentTable rows={data.recent_listings} />
        </CardContent>
      </Card>
    </div>
  );
}

function RecentTable({ rows }: { rows: ListingSummary[] }) {
  if (!rows.length) {
    return <p className="text-sm text-muted-foreground">No listings yet.</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-14" />
          <TableHead>Title</TableHead>
          <TableHead>Price</TableHead>
          <TableHead>Profit est.</TableHead>
          <TableHead>Seen</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.id}>
            <TableCell className="align-top">
              <ListingThumb urls={r.image_urls} alt="" sizeClass="h-9 w-9" />
            </TableCell>
            <TableCell className="max-w-[240px]">
              <Link
                href={`/listings/detail/?id=${r.id}`}
                className="line-clamp-2 text-primary hover:underline"
              >
                {r.title || r.ebay_item_id}
              </Link>
            </TableCell>
            <TableCell>{money(r.current_price, r.currency)}</TableCell>
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
            <TableCell className="text-muted-foreground text-xs">
              {dateShort(r.last_seen_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
