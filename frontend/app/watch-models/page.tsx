"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchJson } from "@/lib/api";
import type { WatchModel, WatchModelListResponse } from "@/lib/types";
import { money } from "@/lib/format";
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
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-border bg-muted/40">
            <tr>
              <th className="px-3 py-2 font-medium">Model</th>
              <th className="px-3 py-2 font-medium">Observed</th>
              <th className="px-3 py-2 font-medium">Manual</th>
              <th className="px-3 py-2 font-medium w-24" />
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-8 text-center text-muted-foreground">
                  No models yet. Add one or widen your search.
                </td>
              </tr>
            ) : (
              rows.map((m) => (
                <tr key={m.id} className="border-b border-border/60">
                  <td className="px-3 py-2">
                    <p className="font-medium">{label(m)}</p>
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
                      <Link href={`/watch-models/detail/?id=${m.id}`}>Edit</Link>
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
