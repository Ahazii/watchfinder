"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiUrl, fetchJson } from "@/lib/api";
import { plainTextFromMaybeHtml } from "@/lib/plain-text";
import { dateShort } from "@/lib/format";
import type {
  AppSettings,
  BackfillWatchCatalogResponse,
  WatchLinkReviewListResponse,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ListingThumb } from "@/components/listing-thumb";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function WatchReviewQueuePage() {
  const [data, setData] = useState<WatchLinkReviewListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [queueRequireIdentity, setQueueRequireIdentity] = useState(true);
  const [queueToggleBusy, setQueueToggleBusy] = useState(false);
  const [notInterestedBusyId, setNotInterestedBusyId] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<"sm" | "md" | "lg">("md");
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

  const load = useCallback(() => {
    setErr(null);
    fetchJson<WatchLinkReviewListResponse>("/api/watch-link-reviews?limit=100")
      .then(setData)
      .catch((e: Error) => setErr(e.message));
  }, []);

  const loadQueueIdentitySetting = useCallback(() => {
    fetchJson<AppSettings>("/api/settings")
      .then((s) => {
        setQueueRequireIdentity(s.watch_catalog_queue_require_identity !== false);
      })
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
    loadQueueIdentitySetting();
  }, [load, loadQueueIdentitySetting]);

  const toggleQueueIdentityRequirement = useCallback(() => {
    setQueueToggleBusy(true);
    setErr(null);
    const next = !queueRequireIdentity;
    fetch(apiUrl("/api/settings"), {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        watch_catalog_queue_require_identity: next,
      }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<AppSettings>;
      })
      .then((s) => {
        setQueueRequireIdentity(s.watch_catalog_queue_require_identity !== false);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setQueueToggleBusy(false));
  }, [queueRequireIdentity]);

  const markNotInterested = useCallback((reviewId: string) => {
    setNotInterestedBusyId(reviewId);
    setErr(null);
    fetch(apiUrl(`/api/watch-link-reviews/${reviewId}/not-interested`), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return fetchJson<WatchLinkReviewListResponse>("/api/watch-link-reviews?limit=100");
      })
      .then(setData)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setNotInterestedBusyId(null));
  }, []);

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
            variant={queueRequireIdentity ? "outline" : "default"}
            disabled={queueToggleBusy}
            onClick={toggleQueueIdentityRequirement}
            title='Toggle queue identity gate: "brand + (reference or model family)".'
          >
            {queueToggleBusy
              ? "Saving…"
              : queueRequireIdentity
                ? "Require identity: ON"
                : "Require identity: OFF"}
          </Button>
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
              <strong className="text-foreground">Require identity</strong> (button above) controls whether
              queueing needs parsed <strong>brand + (reference or model family)</strong>. Turn it{" "}
              <strong>off</strong> to include identity-poor listings for manual review.
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
          <div className="flex items-center justify-end gap-2">
            <label htmlFor="match-queue-image-size" className="text-xs text-muted-foreground">
              Picture size
            </label>
            <select
              id="match-queue-image-size"
              className="h-8 rounded-md border border-border bg-background px-2 text-xs"
              value={imageSize}
              onChange={(e) => setImageSize(e.target.value as "sm" | "md" | "lg")}
            >
              <option value="sm">Small</option>
              <option value="md">Medium</option>
              <option value="lg">Large</option>
            </select>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-28">Photo</TableHead>
                <TableHead className="min-w-[26rem]">Title / Description</TableHead>
                <TableHead className="w-56">eBay</TableHead>
                <TableHead className="w-52">Match Signals</TableHead>
                <TableHead className="w-72">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((row) => {
                const thumbSizeClass =
                  imageSize === "lg"
                    ? "h-24 w-24"
                    : imageSize === "sm"
                      ? "h-12 w-12"
                      : "h-16 w-16";
                const isExpanded = expandedRows[row.id] === true;
                return (
                  <TableRow key={row.id}>
                    <TableCell className="align-top">
                      <ListingThumb
                        urls={row.listing_image_urls}
                        alt={row.listing_title || row.ebay_item_id}
                        sizeClass={thumbSizeClass}
                      />
                    </TableCell>
                    <TableCell className="align-top">
                      <p className={`text-sm font-medium leading-snug ${isExpanded ? "" : "line-clamp-5"}`}>
                        {row.listing_title || row.ebay_item_id}
                      </p>
                      {row.listing_description ? (
                        <p
                          className={`mt-1 text-xs leading-snug text-muted-foreground ${isExpanded ? "" : "line-clamp-6"}`}
                        >
                          {plainTextFromMaybeHtml(row.listing_description)}
                        </p>
                      ) : null}
                      {row.listing_description ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="mt-1 h-7 px-2 text-xs"
                          onClick={() =>
                            setExpandedRows((prev) => ({
                              ...prev,
                              [row.id]: !isExpanded,
                            }))
                          }
                        >
                          {isExpanded ? "Show less" : "Show more"}
                        </Button>
                      ) : null}
                    </TableCell>
                    <TableCell className="align-top">
                      <p className="text-xs text-muted-foreground">Item ID</p>
                      <p className="font-mono text-xs">{row.ebay_item_id}</p>
                      {row.listing_web_url ? (
                        <Button variant="outline" size="sm" asChild className="mt-2">
                          <a href={row.listing_web_url} target="_blank" rel="noopener noreferrer">
                            Open eBay (new window)
                          </a>
                        </Button>
                      ) : null}
                      {row.buying_options?.length ? (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Sale type: {row.buying_options.join(", ")}
                        </p>
                      ) : null}
                      {row.listing_ended_at ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Ends: {dateShort(row.listing_ended_at)}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell className="align-top text-xs text-muted-foreground">
                      <p>
                        tier {row.tier ?? "—"} · {row.candidate_count} candidate(s)
                        {row.confidence != null && row.confidence !== ""
                          ? ` · score ${row.confidence}`
                          : ""}
                      </p>
                      {row.reason_codes?.length ? <p className="mt-1">{row.reason_codes.join(", ")}</p> : null}
                    </TableCell>
                    <TableCell className="align-top">
                      <div className="flex flex-wrap gap-2">
                        <Button asChild size="sm">
                          <Link href={`/watch-review/detail/?id=${row.id}`}>Review</Link>
                        </Button>
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/listings/detail/?id=${row.listing_id}`}>Open in WatchFinder</Link>
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={notInterestedBusyId === row.id}
                          onClick={() => markNotInterested(row.id)}
                          title="Remove listing and block this eBay item id from future ingest"
                        >
                          {notInterestedBusyId === row.id ? "…" : "Not interested"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </>
      )}
    </div>
  );
}
