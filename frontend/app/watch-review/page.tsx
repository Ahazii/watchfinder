"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchJson } from "@/lib/api";
import type { WatchLinkReviewListResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function WatchReviewQueuePage() {
  const [data, setData] = useState<WatchLinkReviewListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    setErr(null);
    fetchJson<WatchLinkReviewListResponse>("/api/watch-link-reviews?limit=100")
      .then(setData)
      .catch((e: Error) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Match queue</h1>
          <p className="mt-1 text-muted-foreground">
            Listings that need a manual decision: link to an existing watch database row, create a
            new row from the listing, or dismiss. Enable this flow in{" "}
            <Link href="/settings/" className="text-primary underline">
              Settings → Watch catalog matching → Review queue
            </Link>
            . On each review detail page, candidate watch rows show <strong>catalog observed</strong> price
            bands in <strong>£ GBP</strong> (from your database), while the eBay listing uses its own
            currency — see <Link href="/settings/" className="text-primary underline">Settings</Link> for a
            full note on money display.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={load}>
          Refresh
        </Button>
      </div>

      {err ? <p className="text-sm text-red-400">{err}</p> : null}

      {!data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : data.total === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>All clear</CardTitle>
            <CardDescription>No pending catalogue reviews.</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{data.total} pending</p>
          <div className="space-y-3">
            {data.items.map((row) => (
              <Card key={row.id}>
                <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 space-y-1">
                    <p className="font-medium line-clamp-2">
                      {row.listing_title || row.ebay_item_id}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      eBay {row.ebay_item_id} · tier {row.tier ?? "—"} ·{" "}
                      {row.candidate_count} candidate(s)
                      {row.confidence != null && row.confidence !== ""
                        ? ` · score ${row.confidence}`
                        : ""}
                    </p>
                    {row.reason_codes?.length ? (
                      <p className="text-xs text-muted-foreground">
                        {row.reason_codes.join(", ")}
                      </p>
                    ) : null}
                  </div>
                  <Button asChild>
                    <Link href={`/watch-review/detail/?id=${row.id}`}>Review</Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
