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

function newLine(): IngestQueryLine {
  return {
    clientKey: crypto.randomUUID(),
    label: "",
    query: "",
    enabled: true,
  };
}

export default function SettingsPage() {
  const [data, setData] = useState<AppSettings | null>(null);
  const [lines, setLines] = useState<IngestQueryLine[]>([]);
  const [intervalMin, setIntervalMin] = useState(30);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    setErr(null);
    fetchJson<AppSettings>("/api/settings")
      .then((d) => {
        setData(d);
        setIntervalMin(d.ingest_interval_minutes);
        setLines(
          d.ingest_queries.length
            ? d.ingest_queries.map((q) => ({
                clientKey: q.id,
                label: q.label,
                query: q.query,
                enabled: q.enabled,
              }))
            : [newLine()],
        );
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
        ingest_queries: payloadQueries,
      }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<AppSettings>;
      })
      .then((d) => {
        setData(d);
        setIntervalMin(d.ingest_interval_minutes);
        setLines(
          d.ingest_queries.length
            ? d.ingest_queries.map((q) => ({
                clientKey: q.id,
                label: q.label,
                query: q.query,
                enabled: q.enabled,
              }))
            : [newLine()],
        );
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
            Disabled lines are skipped. With <strong>no saved lines</strong> (or all empty), the app
            uses the server env default: <code className="rounded bg-muted px-1">{data.env_fallback_query}</code>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong>Repair-sourcing ideas:</strong> mix condition intent (
            <em>spares, not working, for parts, repair</em>) with watch type (
            <em>pocket watch, military, WW2</em>) or brand — one combination per line often works
            better than dozens of tiny searches. Tune <strong>EBAY_SEARCH_LIMIT</strong> in Docker (
            {data.ebay_search_limit} per query per run) to cap API volume.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ingest interval</CardTitle>
          <CardDescription>Minutes between automatic ingest cycles (5–1440).</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-1">
            <label htmlFor="interval" className="text-sm font-medium">
              Minutes
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Browse search lines</CardTitle>
          <CardDescription>
            Add one eBay keyword search per row. Empty rows are ignored when saving.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
                onClick={() => setLines(lines.filter((_, i) => i !== idx))}
              >
                Remove
              </Button>
            </div>
          ))}
          <Button type="button" variant="secondary" onClick={() => setLines([...lines, newLine()])}>
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
