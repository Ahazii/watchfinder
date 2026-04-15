"use client";

import { useCallback, useEffect, useState } from "react";
import { apiUrl, fetchJson } from "@/lib/api";
import type { ActiveRefreshStatus, AppSettings, IngestQueryLine } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** randomUUID() is not available on http:// LAN origins in some browsers — breaks "Add line" silently. */
function newClientKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID();
    } catch {
      /* insecure context */
    }
  }
  return `k-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

function newEmptyLine(): IngestQueryLine {
  return {
    clientKey: newClientKey(),
    label: "",
    query: "",
    enabled: true,
  };
}

/** Show saved rows, or one row pre-filled with the server env default (e.g. wristwatch). */
function linesFromSettings(d: AppSettings): IngestQueryLine[] {
  if (d.ingest_queries.length > 0) {
    return d.ingest_queries.map((q) => ({
      clientKey: q.id,
      label: q.label,
      query: q.query,
      enabled: q.enabled,
    }));
  }
  const q = (d.env_fallback_query || "").trim();
  return [
    {
      clientKey: newClientKey(),
      label: "Default (server env)",
      query: q,
      enabled: true,
    },
  ];
}

export default function SettingsPage() {
  const [data, setData] = useState<AppSettings | null>(null);
  const [lines, setLines] = useState<IngestQueryLine[]>([]);
  const [intervalMin, setIntervalMin] = useState(30);
  const [searchLimit, setSearchLimit] = useState(50);
  const [maxPages, setMaxPages] = useState(1);
  const [catalogReviewMode, setCatalogReviewMode] = useState<"auto" | "review">("auto");
  const [queueRequireIdentity, setQueueRequireIdentity] = useState(true);
  const [catalogExcludedWords, setCatalogExcludedWords] = useState("");
  const [ewLoginEmail, setEwLoginEmail] = useState("");
  const [ewLoginPassword, setEwLoginPassword] = useState("");
  const [ewPasswordConfigured, setEwPasswordConfigured] = useState(false);
  const [ewCredBusy, setEwCredBusy] = useState(false);
  const [staleRefreshEnabled, setStaleRefreshEnabled] = useState(false);
  const [staleRefreshInterval, setStaleRefreshInterval] = useState(360);
  const [staleRefreshMax, setStaleRefreshMax] = useState(20);
  const [staleRefreshMinAge, setStaleRefreshMinAge] = useState(12);
  const [matchQueueSyncInterval, setMatchQueueSyncInterval] = useState(60);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);
  const [activeRefreshStatus, setActiveRefreshStatus] = useState<ActiveRefreshStatus | null>(null);
  const [activeRefreshMsg, setActiveRefreshMsg] = useState<string | null>(null);
  const [activeCheckAllBusy, setActiveCheckAllBusy] = useState(false);
  const [applyExcludedBusy, setApplyExcludedBusy] = useState(false);

  const load = useCallback(() => {
    setErr(null);
    fetchJson<AppSettings>("/api/settings")
      .then((d) => {
        setData(d);
        setIntervalMin(d.ingest_interval_minutes);
        setSearchLimit(d.ebay_search_limit);
        setMaxPages(d.ingest_max_pages ?? 1);
        setCatalogReviewMode(
          d.watch_catalog_review_mode === "review" ? "review" : "auto",
        );
        setQueueRequireIdentity(d.watch_catalog_queue_require_identity !== false);
        setCatalogExcludedWords(d.watch_catalog_excluded_brands ?? "");
        setEwLoginEmail(d.everywatch_login_email ?? "");
        setEwLoginPassword("");
        setEwPasswordConfigured(Boolean(d.everywatch_password_configured));
        setStaleRefreshEnabled(Boolean(d.stale_listing_refresh_enabled));
        setStaleRefreshInterval(d.stale_listing_refresh_interval_minutes ?? 360);
        setStaleRefreshMax(d.stale_listing_refresh_max_per_run ?? 20);
        setStaleRefreshMinAge(d.stale_listing_refresh_min_age_hours ?? 12);
        setMatchQueueSyncInterval(d.match_queue_sync_interval_minutes ?? 60);
        setLines(linesFromSettings(d));
      })
      .catch((e: Error) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadActiveRefreshStatus = useCallback(() => {
    fetchJson<ActiveRefreshStatus>("/api/ingest/active-refresh-all-status")
      .then(setActiveRefreshStatus)
      .catch(() => {
        // Keep UI usable if polling fails.
      });
  }, []);

  useEffect(() => {
    loadActiveRefreshStatus();
  }, [loadActiveRefreshStatus]);

  useEffect(() => {
    if (!activeRefreshStatus?.running) return;
    const h = window.setInterval(() => {
      loadActiveRefreshStatus();
    }, 1200);
    return () => window.clearInterval(h);
  }, [activeRefreshStatus?.running, loadActiveRefreshStatus]);

  const save = () => {
    const payloadQueries = lines
      .map((l) => ({
        label: l.label.trim(),
        query: l.query.trim(),
        enabled: l.enabled,
      }))
      .filter((l) => l.query.length > 0);

    setSaving(true);
    setErr(null);
    const patchBody: Record<string, unknown> = {
      ingest_interval_minutes: intervalMin,
      ebay_search_limit: searchLimit,
      ingest_max_pages: maxPages,
      ingest_queries: payloadQueries,
      watch_catalog_review_mode: catalogReviewMode,
      watch_catalog_queue_require_identity: queueRequireIdentity,
      watch_catalog_excluded_brands: catalogExcludedWords,
      everywatch_login_email: ewLoginEmail.trim(),
      stale_listing_refresh_enabled: staleRefreshEnabled,
      stale_listing_refresh_interval_minutes: staleRefreshInterval,
      stale_listing_refresh_max_per_run: staleRefreshMax,
      stale_listing_refresh_min_age_hours: staleRefreshMinAge,
      match_queue_sync_interval_minutes: matchQueueSyncInterval,
    };
    if (ewLoginPassword.trim()) {
      patchBody.everywatch_login_password = ewLoginPassword;
    }
    fetch(apiUrl("/api/settings"), {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(patchBody),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<AppSettings>;
      })
      .then((d) => {
        setData(d);
        setIntervalMin(d.ingest_interval_minutes);
        setSearchLimit(d.ebay_search_limit);
        setMaxPages(d.ingest_max_pages ?? 1);
        setCatalogReviewMode(
          d.watch_catalog_review_mode === "review" ? "review" : "auto",
        );
        setQueueRequireIdentity(d.watch_catalog_queue_require_identity !== false);
        setCatalogExcludedWords(d.watch_catalog_excluded_brands ?? "");
        setEwLoginEmail(d.everywatch_login_email ?? "");
        setEwLoginPassword("");
        setEwPasswordConfigured(Boolean(d.everywatch_password_configured));
        setStaleRefreshEnabled(Boolean(d.stale_listing_refresh_enabled));
        setStaleRefreshInterval(d.stale_listing_refresh_interval_minutes ?? 360);
        setStaleRefreshMax(d.stale_listing_refresh_max_per_run ?? 20);
        setStaleRefreshMinAge(d.stale_listing_refresh_min_age_hours ?? 12);
        setMatchQueueSyncInterval(d.match_queue_sync_interval_minutes ?? 60);
        setLines(linesFromSettings(d));
        setEwLoginPassword("");
        setEwPasswordConfigured(Boolean(d.everywatch_password_configured));
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setSaving(false));
  };

  const clearEverywatchPassword = () => {
    setEwCredBusy(true);
    setErr(null);
    fetch(apiUrl("/api/settings"), {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ everywatch_login_password: "" }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<AppSettings>;
      })
      .then((d) => {
        setEwPasswordConfigured(Boolean(d.everywatch_password_configured));
        setEwLoginPassword("");
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setEwCredBusy(false));
  };

  const ingestNow = () => {
    setIngestMsg(null);
    fetchJson<{ status: string; message: string }>("/api/ingest/run", {
      method: "POST",
    })
      .then((r) => setIngestMsg(r.message))
      .catch((e: Error) => setIngestMsg(e.message));
  };

  const staleRefreshNow = () => {
    setIngestMsg(null);
    fetchJson<{ status: string; message: string }>("/api/ingest/stale-refresh-run", {
      method: "POST",
    })
      .then((r) => setIngestMsg(r.message))
      .catch((e: Error) => setIngestMsg(e.message));
  };

  const fullActiveRefreshNow = () => {
    setActiveRefreshMsg(null);
    fetchJson<{ status: string; message: string }>("/api/ingest/active-refresh-all-run", {
      method: "POST",
    })
      .then((r) => {
        setActiveRefreshMsg(r.message);
        loadActiveRefreshStatus();
      })
      .catch((e: Error) => setActiveRefreshMsg(e.message));
  };

  const checkActiveAllNow = () => {
    setActiveRefreshMsg(null);
    setActiveCheckAllBusy(true);
    fetchJson<{
      status: string;
      total: number;
      updated: number;
      active_now: number;
      inactive_now: number;
    }>("/api/ingest/recompute-active-from-end-date", {
      method: "POST",
    })
      .then((r) => {
        setActiveRefreshMsg(
          `Check Active (All) complete: scanned ${r.total}, updated ${r.updated}, active ${r.active_now}, inactive ${r.inactive_now}.`,
        );
      })
      .catch((e: Error) => setActiveRefreshMsg(e.message))
      .finally(() => setActiveCheckAllBusy(false));
  };

  const applyExcludedWordsNow = () => {
    setActiveRefreshMsg(null);
    setApplyExcludedBusy(true);
    fetchJson<{
      status: string;
      scanned: number;
      matched: number;
      updated: number;
    }>("/api/ingest/apply-excluded-words-all", {
      method: "POST",
    })
      .then((r) => {
        setActiveRefreshMsg(
          `Apply excluded words complete: scanned ${r.scanned}, matched ${r.matched}, marked inactive ${r.updated}.`,
        );
      })
      .catch((e: Error) => setActiveRefreshMsg(e.message))
      .finally(() => setApplyExcludedBusy(false));
  };

  if (err && !data) {
    return (
      <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-red-200">
        <p className="font-medium">Could not load settings</p>
        <p className="mt-1 text-sm opacity-90">{err}</p>
      </div>
    );
  }

  if (!data) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Browse search strings, ingest timing, watch-catalog behaviour, stale listing refresh, and manual
          API runs. Marketplace and pricing on listings come from your eBay app config (see{" "}
          <code className="rounded bg-muted px-1">EBAY_MARKETPLACE_ID</code> in{" "}
          <code className="rounded bg-muted px-1">.env.example</code>).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Prices &amp; currencies in the UI</CardTitle>
          <CardDescription>
            This page does not edit money fields. Elsewhere in the app: <strong>watch database</strong> manual
            and observed bounds are stored and shown in <strong>British pounds (£)</strong>.{" "}
            <strong>eBay listing</strong> prices, shipping, scores, and your per-listing valuation inputs are
            shown in <strong>that listing’s currency</strong> (symbols from eBay, e.g. £ / $ / €).{" "}
            <strong>WatchBase</strong> imported chart points stay in <strong>euros (€)</strong> until converted
            to GBP for manual bounds on import. List/candidate <strong>price filters</strong> compare plain
            numbers as stored — they do not convert between currencies.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>How searches work</CardTitle>
          <CardDescription>
            Each <strong>line</strong> is one eBay Browse search (<code className="rounded bg-muted px-1">q</code>
            ). eBay treats it as keywords, not Boolean algebra — combine words on one line for
            phrases like <em>pocket watch spares repair</em>. Use <strong>several lines</strong> for
            different angles (e.g. one for brands, one for &quot;broken&quot;, one for military).
            Disabled lines are skipped. Until you click <strong>Save</strong>, the first row shows
            your server env default (<code className="rounded bg-muted px-1">{data.env_fallback_query}</code>
            ) so you can edit it or add more lines.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong>Repair-sourcing ideas:</strong> mix condition intent (
            <em>spares, not working, for parts, repair</em>) with watch type (
            <em>pocket watch, military, WW2</em>) or brand — one combination per line often works
            better than dozens of tiny searches.
          </p>
          <p>
            <strong>Throughput:</strong> each enabled line runs one Browse API search per cycle.
            You get at most <em>items per search × number of lines</em> new/updated summaries per
            cycle (capped by eBay at 200 per search). Multiply by cycles per day (60 / interval
            minutes) for a rough daily ceiling — stay within{" "}
            <a
              className="text-primary underline-offset-4 hover:underline"
              href="https://developer.ebay.com/api-docs/static/rest-rate-limiting-API.html"
              target="_blank"
              rel="noreferrer"
            >
              eBay rate limits
            </a>
            .
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Watch catalog matching</CardTitle>
          <CardDescription>
            When <strong>Review queue</strong> is on, only exact brand+reference or brand+family
            matches link automatically. Everything else (fuzzy title, or creating a new catalog row)
            goes to the <strong>Match queue</strong> for you to confirm. Candidate rows on the queue
            show <strong>catalog observed</strong> ranges in <strong>£ GBP</strong> (aggregated from
            linked listings and recorded sales for that watch model — not the listing’s own currency).
            <span className="mt-2 block text-xs">
              <strong className="text-foreground">Hints:</strong> Use <strong>Match queue sync</strong> so
              active listings without a catalog link are re-analyzed on a timer — same logic as ingest, without
              waiting for the next Browse search. Set <strong>0</strong> minutes to rely only on ingest +
              manual <strong>Sync unmatched</strong> on the Match queue page. In <strong>Automatic</strong>{" "}
              mode, that job links or creates catalog rows instead of enqueueing.
            </span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <label className="text-sm font-medium" htmlFor="wcrm">
            Mode
          </label>
          <select
            id="wcrm"
            className="flex h-9 max-w-md rounded-md border border-border bg-background px-2 text-sm"
            value={catalogReviewMode}
            onChange={(e) =>
              setCatalogReviewMode(e.target.value === "review" ? "review" : "auto")
            }
          >
            <option value="auto">Automatic — fuzzy match + create catalog rows without queue</option>
            <option value="review">Review queue — exact matches only; queue the rest</option>
          </select>
          <div className="pt-2">
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border"
                checked={queueRequireIdentity}
                onChange={(e) => setQueueRequireIdentity(e.target.checked)}
              />
              Require parsed identity for queue entries (brand + reference/family)
            </label>
            <p className="mt-1 text-xs text-muted-foreground">
              When disabled in <strong>Review queue</strong> mode, listings without full identity can still be
              enqueued for manual decision instead of being skipped as no-identity.
            </p>
          </div>
          <div className="pt-2">
            <label className="text-sm font-medium" htmlFor="mq-sync">
              Match queue — sync from unmatched listings (minutes)
            </label>
            <p className="mt-1 text-xs text-muted-foreground">
              Periodically re-analyze <strong>active</strong> listings that still have <strong>no</strong> watch
              database link so they appear in the match queue (review mode) or get auto-linked (automatic mode).{" "}
              <strong>0</strong> disables the background job; use the button on the Match queue page to run it
              anytime. Typical values: <strong>30–120</strong> minutes if you ingest often; lower if you only
              run ingest occasionally and want the queue to catch up between runs.
            </p>
            <Input
              id="mq-sync"
              type="number"
              min={0}
              max={1440}
              className="mt-2 max-w-[120px]"
              value={matchQueueSyncInterval}
              onChange={(e) => setMatchQueueSyncInterval(Number(e.target.value))}
              title="Minutes between scheduler runs. 0 = off. Persisted in app_settings; env MATCH_QUEUE_SYNC_INTERVAL_MINUTES is the default before first save."
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listings — excluded words/phrases</CardTitle>
          <CardDescription>
            Comma-separated words or short phrases (case-insensitive, whole-word matching), e.g.{" "}
            <code className="rounded bg-muted px-1">replica, smartwatch, kids watch</code>. Any listing that
            matches one of these terms is forced inactive and blocked from being reactivated by ingest/refresh.
            This field is <strong>merged</strong> with the server
            environment variable <code className="rounded bg-muted px-1">WATCH_CATALOG_EXCLUDED_BRANDS</code> (both apply).
            Clear this field to rely on env-only exclusions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <label className="text-sm font-medium" htmlFor="wc-excl">
            Excluded words/phrases
          </label>
          <textarea
            id="wc-excl"
            className="min-h-[88px] w-full max-w-2xl rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="replica, fake, smartwatch"
            value={catalogExcludedWords}
            onChange={(e) => setCatalogExcludedWords(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Use comma-separated terms. Matching is case-insensitive with whole-word boundaries.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Everywatch login (optional)</CardTitle>
          <CardDescription>
            Stored in your <strong>Postgres</strong> <code className="rounded bg-muted px-1">app_settings</code> as{" "}
            <strong>plaintext</strong> (self-hosted / hobby use only). Used by{" "}
            <strong>Everywatch import tester</strong> to call{" "}
            <code className="rounded bg-muted px-1">POST https://api.everywatch.com/api/Auth/Login</code> and attach
            session cookies to debug fetches. Comply with Everywatch terms; rotate credentials if the database is
            exposed.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Saved password:{" "}
            <strong className="text-foreground">{ewPasswordConfigured ? "yes" : "no"}</strong>
          </p>
          <div>
            <label className="mb-1 block text-sm font-medium" htmlFor="ew-email">
              Email (userName)
            </label>
            <Input
              id="ew-email"
              type="email"
              autoComplete="off"
              value={ewLoginEmail}
              onChange={(e) => setEwLoginEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium" htmlFor="ew-pass">
              Password
            </label>
            <Input
              id="ew-pass"
              type="password"
              autoComplete="new-password"
              placeholder={
                ewPasswordConfigured ? "Leave blank to keep current password" : "Enter password to save"
              }
              value={ewLoginPassword}
              onChange={(e) => setEwLoginPassword(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={ewCredBusy || !ewPasswordConfigured}
              onClick={() => void clearEverywatchPassword()}
            >
              {ewCredBusy ? "…" : "Remove saved password"}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Saving the main <strong>Save</strong> button below persists email and (if filled) password.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Stale listing refresh (getItem)</CardTitle>
          <CardDescription>
            Periodically re-fetch <strong>active</strong> listings whose{" "}
            <code className="rounded bg-muted px-1">last_seen_at</code> is older than the minimum age.
            Each run calls Browse <strong>getItem</strong> up to the max count, with a short pause
            between calls. Ended listings are marked inactive (same as detail page refresh).{" "}
            <strong>Min age</strong> skips recently seen rows (e.g. after ingest); use <strong>0</strong> to
            refresh any active listing whose <code className="rounded bg-muted px-1">last_seen_at</code> is
            already in the past.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border"
              checked={staleRefreshEnabled}
              onChange={(e) => setStaleRefreshEnabled(e.target.checked)}
            />
            Enable scheduled stale refresh
          </label>
          <div className="flex flex-wrap items-end gap-6">
            <div className="space-y-1">
              <label htmlFor="staleInt" className="text-sm font-medium">
                Interval (minutes)
              </label>
              <Input
                id="staleInt"
                type="number"
                min={15}
                max={1440}
                className="w-32"
                value={staleRefreshInterval}
                onChange={(e) => setStaleRefreshInterval(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="staleMax" className="text-sm font-medium">
                Max listings per run
              </label>
              <Input
                id="staleMax"
                type="number"
                min={1}
                max={100}
                className="w-32"
                value={staleRefreshMax}
                onChange={(e) => setStaleRefreshMax(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="staleAge" className="text-sm font-medium">
                Min age (hours)
              </label>
              <Input
                id="staleAge"
                type="number"
                min={0}
                max={720}
                className="w-32"
                value={staleRefreshMinAge}
                onChange={(e) => setStaleRefreshMinAge(Number(e.target.value))}
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Env defaults: <code className="rounded bg-muted px-1">STALE_LISTING_REFRESH_*</code> until
            you save. Manual run uses current limits regardless of the schedule checkbox.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ingest timing &amp; page size</CardTitle>
          <CardDescription>
            Interval controls how often the scheduler runs; <strong>items per search line</strong> is
            the Browse page size (1–200). <strong>Pages per line</strong> is how many offsets to fetch
            (1 = first page only; 3 = up to 3× that many hits per line, 3× the API calls). Env{" "}
            <code className="rounded bg-muted px-1">EBAY_SEARCH_LIMIT</code> /{" "}
            <code className="rounded bg-muted px-1">INGEST_MAX_PAGES</code> apply until you save here.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-6">
          <div className="space-y-1">
            <label htmlFor="interval" className="text-sm font-medium">
              Interval (minutes)
            </label>
            <Input
              id="interval"
              type="number"
              min={5}
              max={1440}
              className="w-32"
              value={intervalMin}
              onChange={(e) => setIntervalMin(Number(e.target.value))}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="searchLimit" className="text-sm font-medium">
              Items per search line
            </label>
            <Input
              id="searchLimit"
              type="number"
              min={1}
              max={200}
              className="w-32"
              value={searchLimit}
              onChange={(e) => setSearchLimit(Number(e.target.value))}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="maxPages" className="text-sm font-medium">
              Pages per search line
            </label>
            <Input
              id="maxPages"
              type="number"
              min={1}
              max={20}
              className="w-32"
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Browse search lines</CardTitle>
          <CardDescription>
            Each row is sent to eBay Browse API as a single <code className="rounded bg-muted px-1">q</code>{" "}
            string: the whole line is <strong>one query</strong>, not split into separate searches. eBay
            tokenizes and matches keywords across title and item specifics; it is not full Boolean (no{" "}
            <code className="rounded bg-muted px-1">AND</code>/<code className="rounded bg-muted px-1">OR</code>{" "}
            syntax). Usually a short phrase on one line works better than one giant blob or many
            single-word lines.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Examples</p>
            <ul className="mt-2 list-inside list-disc space-y-1">
              <li>
                <span className="text-foreground">Good:</span>{" "}
                <code className="rounded bg-background px-1">omega seamaster 300 vintage</code> — tight
                intent on one line.
              </li>
              <li>
                <span className="text-foreground">Good:</span> several lines for different intents — e.g.{" "}
                <code className="rounded bg-background px-1">pocket watch not working</code> and{" "}
                <code className="rounded bg-background px-1">military wristwatch spares</code>.
              </li>
              <li>
                <span className="text-foreground">Weak:</span> one line with twenty unrelated words; the
                match becomes noisy.
              </li>
              <li>
                <span className="text-foreground">Weak:</span> expecting the UI to run each word as its own
                search — it does not; only whole-line queries run.
              </li>
            </ul>
          </div>
          {lines.map((line, idx) => (
            <div
              key={line.clientKey}
              className="flex flex-col gap-3 rounded-lg border border-border p-4 sm:flex-row sm:flex-wrap sm:items-center"
            >
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={line.enabled}
                  onChange={(e) => {
                    const next = [...lines];
                    next[idx] = { ...line, enabled: e.target.checked };
                    setLines(next);
                  }}
                  className="h-4 w-4 rounded border-border"
                />
                On
              </label>
              <Input
                placeholder="Label (optional)"
                className="sm:max-w-[200px]"
                value={line.label}
                onChange={(e) => {
                  const next = [...lines];
                  next[idx] = { ...line, label: e.target.value };
                  setLines(next);
                }}
              />
              <Input
                placeholder='e.g. wristwatch broken repair'
                className="min-w-[200px] flex-1"
                value={line.query}
                onChange={(e) => {
                  const next = [...lines];
                  next[idx] = { ...line, query: e.target.value };
                  setLines(next);
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setLines((prev) => prev.filter((_, i) => i !== idx))}
              >
                Remove
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="secondary"
            onClick={() => setLines((prev) => [...prev, newEmptyLine()])}
          >
            Add search line
          </Button>
        </CardContent>
      </Card>

      {err ? (
        <p className="text-sm text-red-400">{err}</p>
      ) : null}
      {ingestMsg ? (
        <p className="text-sm text-muted-foreground">{ingestMsg}</p>
      ) : null}
      {activeRefreshMsg ? (
        <p className="text-sm text-muted-foreground">{activeRefreshMsg}</p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Save &amp; manual jobs</CardTitle>
          <CardDescription>
            <strong>Save settings</strong> writes this form to the database (and affects the next scheduler
            runs). <strong>Ingest now</strong> queues a full Browse search cycle in the background (same as
            the timer): check container logs for progress or errors. <strong>Stale refresh now</strong> runs
            one batch of <strong>getItem</strong> calls using the max-per-run and min-age limits above,
            independent of the schedule checkbox — useful to test after changing those numbers.
            <strong>Check Active (All)</strong> recomputes active flags from stored eBay end dates only
            (fast DB pass, no eBay calls). <strong>Apply excluded words (All)</strong> scans existing listings
            and marks matched rows inactive. <strong>Refresh ALL active now</strong> performs live eBay checks
            for currently active rows.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button type="button" disabled={saving} onClick={save}>
            {saving ? "Saving…" : "Save settings"}
          </Button>
          <Button type="button" variant="outline" onClick={ingestNow}>
            Ingest now
          </Button>
          <Button type="button" variant="outline" onClick={staleRefreshNow}>
            Stale refresh now
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={activeCheckAllBusy}
            onClick={checkActiveAllNow}
            title="Recompute is_active across all rows using listing end date only (no external API calls)."
          >
            {activeCheckAllBusy ? "Checking…" : "Check Active (All)"}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={applyExcludedBusy}
            onClick={applyExcludedWordsNow}
            title="Scans all listings and marks inactive rows that match any excluded word/phrase."
          >
            {applyExcludedBusy ? "Applying…" : "Apply excluded words (All)"}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={Boolean(activeRefreshStatus?.running)}
            onClick={fullActiveRefreshNow}
            title="Checks every currently active listing with adaptive pacing/backoff and reports live progress."
          >
            {activeRefreshStatus?.running ? "Active refresh running…" : "Refresh ALL active now"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active refresh progress</CardTitle>
          <CardDescription>
            Live progress for full active checks across all active rows. Status values reflect the latest item
            check result from the server.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {!activeRefreshStatus ? (
            <p className="text-muted-foreground">Status unavailable.</p>
          ) : (
            <>
              <p>
                {activeRefreshStatus.running ? "Running" : "Idle"} · item{" "}
                <strong>
                  {activeRefreshStatus.current_index || activeRefreshStatus.processed}
                </strong>{" "}
                of <strong>{activeRefreshStatus.total}</strong>
              </p>
              <p>
                Updated active: <strong>{activeRefreshStatus.updated}</strong> · Marked not active:{" "}
                <strong>{activeRefreshStatus.ended}</strong> · Errors:{" "}
                <strong>{activeRefreshStatus.errors}</strong>
              </p>
              <p>
                Current item: <code className="rounded bg-muted px-1">
                  {activeRefreshStatus.current_item_id || "—"}
                </code>{" "}
                · Status: <strong>{activeRefreshStatus.last_status || "—"}</strong>
              </p>
              {activeRefreshStatus.last_error ? (
                <p className="text-red-400">{activeRefreshStatus.last_error}</p>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
