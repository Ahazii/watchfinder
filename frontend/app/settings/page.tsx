"use client";

import { useCallback, useEffect, useState } from "react";
import { apiUrl, fetchJson } from "@/lib/api";
import type { AppSettings, IngestQueryLine } from "@/lib/types";
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
  const [catalogReviewMode, setCatalogReviewMode] = useState<"auto" | "review">("auto");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    setErr(null);
    fetchJson<AppSettings>("/api/settings")
      .then((d) => {
        setData(d);
        setIntervalMin(d.ingest_interval_minutes);
        setSearchLimit(d.ebay_search_limit);
        setCatalogReviewMode(
          d.watch_catalog_review_mode === "review" ? "review" : "auto",
        );
        setLines(linesFromSettings(d));
      })
      .catch((e: Error) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
    fetch(apiUrl("/api/settings"), {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ingest_interval_minutes: intervalMin,
        ebay_search_limit: searchLimit,
        ingest_queries: payloadQueries,
        watch_catalog_review_mode: catalogReviewMode,
      }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<AppSettings>;
      })
      .then((d) => {
        setData(d);
        setIntervalMin(d.ingest_interval_minutes);
        setSearchLimit(d.ebay_search_limit);
        setCatalogReviewMode(
          d.watch_catalog_review_mode === "review" ? "review" : "auto",
        );
        setLines(linesFromSettings(d));
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setSaving(false));
  };

  const ingestNow = () => {
    setIngestMsg(null);
    fetchJson<{ status: string; message: string }>("/api/ingest/run", {
      method: "POST",
    })
      .then((r) => setIngestMsg(r.message))
      .catch((e: Error) => setIngestMsg(e.message));
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
          Browse search strings, ingest timing, and manual runs.
        </p>
      </div>

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
            goes to the <strong>Match queue</strong> for you to confirm.
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ingest timing &amp; page size</CardTitle>
          <CardDescription>
            Interval controls how often the scheduler runs; page size is how many hits eBay returns
            per search line (1–200). Env <code className="rounded bg-muted px-1">EBAY_SEARCH_LIMIT</code>{" "}
            applies until you save here once — then this UI value is stored in the database.
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

      <div className="flex flex-wrap gap-3">
        <Button type="button" disabled={saving} onClick={save}>
          {saving ? "Saving…" : "Save settings"}
        </Button>
        <Button type="button" variant="outline" onClick={ingestNow}>
          Ingest now
        </Button>
      </div>
    </div>
  );
}
