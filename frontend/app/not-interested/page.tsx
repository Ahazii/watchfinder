"use client";

import { useCallback, useEffect, useState } from "react";
import { apiUrl, fetchJson } from "@/lib/api";
import type { NotInterestedListResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function NotInterestedPage() {
  const [data, setData] = useState<NotInterestedListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);

  const load = useCallback(() => {
    setErr(null);
    const qs = new URLSearchParams();
    qs.set("limit", "500");
    qs.set("active_only", activeOnly ? "true" : "false");
    if (q.trim()) qs.set("q", q.trim());
    fetchJson<NotInterestedListResponse>(`/api/not-interested?${qs.toString()}`)
      .then(setData)
      .catch((e: Error) => setErr(e.message));
  }, [activeOnly, q]);

  useEffect(() => {
    load();
  }, [load]);

  const restore = (id: string) => {
    setBusyId(id);
    setErr(null);
    fetch(apiUrl(`/api/not-interested/${id}/restore`), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
      })
      .then(load)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusyId(null));
  };

  const hardDelete = (id: string) => {
    setBusyId(id);
    setErr(null);
    fetch(apiUrl(`/api/not-interested/${id}`), {
      method: "DELETE",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
      })
      .then(load)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusyId(null));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Not interested</h1>
        <p className="mt-1 text-muted-foreground">
          Listings marked not interested are blocked by eBay item id and skipped during ingest.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Search by eBay id or remembered listing title.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Search id or title"
              className="max-w-sm"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(e) => setActiveOnly(e.target.checked)}
              />
              Active blocklist only
            </label>
            <Button variant="outline" onClick={load}>
              Refresh
            </Button>
          </div>
          {err ? <p className="text-sm text-red-400">{err}</p> : null}
        </CardContent>
      </Card>

      {!data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : data.items.length === 0 ? (
        <p className="text-muted-foreground">No records.</p>
      ) : (
        <div className="space-y-3">
          {data.items.map((row) => (
            <Card key={row.id}>
              <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <p className="font-medium">{row.last_listing_title || row.ebay_item_id}</p>
                  <p className="text-xs text-muted-foreground">
                    eBay {row.ebay_item_id} · {row.is_active ? "blocked" : "restored"} ·{" "}
                    {row.reason || "not_interested"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={busyId === row.id || !row.is_active}
                    onClick={() => restore(row.id)}
                  >
                    {busyId === row.id ? "…" : "I am interested"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={busyId === row.id}
                    onClick={() => hardDelete(row.id)}
                    title="Remove this history record permanently."
                  >
                    Delete record
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
