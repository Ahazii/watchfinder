"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiUrl, fetchJson } from "@/lib/api";
import type { BackfillWatchCatalogResponse, WatchLinkReviewListResponse } from "@/lib/types";
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
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    setErr(null);
    fetchJson<WatchLinkReviewListResponse>("/api/watch-link-reviews?limit=100")
      .then(setData)
      .catch((e: Error) => setErr(e.message));
  }, []);

  const syncUnmatched = useCallback(() => {
    setSyncBusy(true);
    setSyncMsg(null);
    setErr(null);
    fetch(apiUrl("/api/watch-link-reviews/sync-from-unmatched"), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<BackfillWatchCatalogResponse>;
      })
      .then((r) => {
        setSyncMsg(
          `Processed ${r.scanned} unmatched listing(s): ${r.queued_for_review ?? 0} queued for review, ` +
            `${r.linked_existing} linked to existing catalog rows, ${r.created_new} new catalog rows, ` +
            `${r.skipped_no_identity} skipped (no identity), ${r.skipped_excluded_brand ?? 0} excluded brand.`,
        );
        return fetchJson<WatchLinkReviewListResponse>("/api/watch-link-reviews?limit=100");
      })
      .then(setData)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setSyncBusy(false));
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
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button
            type="button"
            variant="default"
            disabled={syncBusy}
            onClick={syncUnmatched}
            title="Re-run catalog matching for every active listing that is not linked to the watch database (same work as scheduled sync and ingest analyze)."
          >
            {syncBusy ? "Syncing…" : "Sync unmatched listings"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={load}
            title="Reload this list from the server without re-analyzing listings."
          >
            Refresh
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Tips</CardTitle>
          <CardDescription>
            Get the most out of the match queue and keep it up to date without living in Settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-inside list-disc space-y-1.5">
            <li>
              <strong className="text-foreground">Review queue mode</strong> is required for items to appear
              here. In <strong>Automatic</strong> mode, the app links or creates catalog rows without asking.
            </li>
            <li>
              <strong className="text-foreground">Sync unmatched</strong> walks every <strong>active</strong>{" "}
              listing with no watch database link, re-parses the title, and either enqueues (review mode) or
              auto-links (automatic mode). Use it after bulk ingest or if you switched catalog modes.
            </li>
            <li>
              Set a <strong className="text-foreground">scheduled sync</strong> in{" "}
              <Link href="/settings/" className="text-primary underline">
                Settings → Match queue — sync from unmatched listings
              </Link>{" "}
              (minutes; <strong>0</strong> turns the background job off). Ingest already analyzes new rows; this
              catches stragglers and re-tries after you improve titles or exclusions.
            </li>
            <li>
              If counts stay at <strong className="text-foreground">skipped (no identity)</strong>, the title
              may not yield brand + reference/family — edit the listing or use{" "}
              <strong>Promote to watch database</strong> on the listing detail page when appropriate.
            </li>
          </ul>
        </CardContent>
      </Card>

      {syncMsg ? <p className="text-sm text-muted-foreground">{syncMsg}</p> : null}
      {err ? <p className="text-sm text-red-400">{err}</p> : null}

      {!data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : data.total === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>All clear</CardTitle>
            <CardDescription>
              No pending catalogue reviews. If you expected rows, confirm{" "}
              <strong>Review queue</strong> mode in Settings, then try{" "}
              <strong>Sync unmatched listings</strong> above — or wait for the next scheduled sync.
            </CardDescription>
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
