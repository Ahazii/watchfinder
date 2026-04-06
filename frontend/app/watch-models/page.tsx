"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiUrl, fetchJson } from "@/lib/api";
import { TABLE_THUMB_STORAGE, usePersistedTableThumbSize } from "@/lib/table-thumb-sizes";
import { TableThumbSizeSelect } from "@/components/table-thumb-size-select";
import type {
  BackfillWatchCatalogResponse,
  WatchModel,
  WatchModelListResponse,
} from "@/lib/types";
import { money } from "@/lib/format";
import { ListingThumb } from "@/components/listing-thumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const PAGE = 50;

export default function WatchModelsPage() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [skip, setSkip] = useState(0);
  const [rows, setRows] = useState<WatchModel[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [backfillBusy, setBackfillBusy] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);
  const { sizeId: thumbSizeId, setSizeId: setThumbSizeId, sizeClass: thumbSizeClass } =
    usePersistedTableThumbSize(TABLE_THUMB_STORAGE.watchDatabase);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    setSkip(0);
  }, [debounced]);

  const load = useCallback(() => {
    setErr(null);
    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(PAGE),
    });
    if (debounced) params.set("q", debounced);
    fetchJson<WatchModelListResponse>(`/api/watch-models?${params}`)
      .then((r) => {
        setRows(r.items);
        setTotal(r.total);
      })
      .catch((e: Error) => setErr(e.message));
  }, [skip, debounced]);

  useEffect(() => {
    load();
  }, [load]);

  const label = (m: WatchModel) => {
    const parts = [m.brand, m.reference, m.model_family].filter(Boolean);
    return parts.join(" · ") || m.id;
  };

  const runBackfill = () => {
    setBackfillBusy(true);
    setBackfillMsg(null);
    fetch(apiUrl("/api/watch-models/backfill-from-listings"), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<BackfillWatchCatalogResponse>;
      })
      .then((r) => {
        setBackfillMsg(
          `Scanned ${r.scanned}: ${r.created_new} new catalog rows, ${r.linked_existing} linked to existing rows, ${r.already_linked} already linked, ${r.queued_for_review ?? 0} queued for review, ${r.skipped_no_identity} skipped (missing brand and reference/family).`,
        );
        load();
      })
      .catch((e: Error) => setBackfillMsg(e.message))
      .finally(() => setBackfillBusy(false));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Watch database</h1>
          <p className="mt-1 text-muted-foreground">
            Canonical models (brand + reference or family). Many listings can link to one row.
            Observed prices update from linked listings and matching sale records.
          </p>
        </div>
        <Button asChild>
          <Link href="/watch-models/detail/">Add model</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Backfill from listings</CardTitle>
          <CardDescription>
            Scan every <strong>active</strong> listing: match the catalog when possible, otherwise
            create a row when brand + reference (or brand + model family) are known. Safe to run more
            than once. Same logic runs automatically when listings are ingested or re-analyzed.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Button type="button" disabled={backfillBusy} onClick={runBackfill}>
            {backfillBusy ? "Running…" : "Run backfill now"}
          </Button>
          {backfillMsg ? (
            <p className="text-sm text-muted-foreground">{backfillMsg}</p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Search</CardTitle>
          <CardDescription>Filter by brand, reference, family, or model name.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Input
            placeholder="Search…"
            className="max-w-md"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </CardContent>
      </Card>

      {err ? <p className="text-sm text-red-400">{err}</p> : null}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[800px] text-left text-sm">
          <thead className="border-b border-border bg-muted/40">
            <tr>
              <th className="px-3 py-2 font-medium align-bottom">
                <div className="flex flex-col items-start gap-1 sm:flex-row sm:items-center sm:gap-2">
                  <span>Photo</span>
                  <TableThumbSizeSelect
                    id="watch-db-thumb-size"
                    compact
                    value={thumbSizeId}
                    onChange={setThumbSizeId}
                  />
                </div>
              </th>
              <th className="px-3 py-2 font-medium">Model</th>
              <th className="px-3 py-2 font-medium">Observed</th>
              <th className="px-3 py-2 font-medium">Manual</th>
              <th className="px-3 py-2 font-medium w-36">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">
                  No models yet. Add one or widen your search.
                </td>
              </tr>
            ) : (
              rows.map((m) => (
                <tr key={m.id} className="border-b border-border/60">
                  <td className="px-3 py-2 align-top">
                    <ListingThumb urls={m.image_urls} alt="" sizeClass={thumbSizeClass} />
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/watch-models/detail/?id=${m.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {label(m)}
                    </Link>
                    {m.model_name ? (
                      <p className="text-xs text-muted-foreground">{m.model_name}</p>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">
                    {money(m.observed_price_low)} – {money(m.observed_price_high)}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">
                    {money(m.manual_price_low)} – {money(m.manual_price_high)}
                  </td>
                  <td className="px-3 py-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/watch-models/detail/?id=${m.id}`}>Details</Link>
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span>
          {total === 0 ? "0" : `${skip + 1}–${Math.min(skip + rows.length, total)}`} of {total}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={skip <= 0}
          onClick={() => setSkip((s) => Math.max(0, s - PAGE))}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={skip + PAGE >= total}
          onClick={() => setSkip((s) => s + PAGE)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
