"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiUrl, fetchJson } from "@/lib/api";
import type { WatchLinkReviewDetail } from "@/lib/types";
import { money } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function WatchReviewDetailPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
      <Body />
    </Suspense>
  );
}

function Body() {
  const sp = useSearchParams();
  const router = useRouter();
  const id = sp.get("id");
  const [row, setRow] = useState<WatchLinkReviewDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!id) return;
    setErr(null);
    fetchJson<WatchLinkReviewDetail>(`/api/watch-link-reviews/${id}`)
      .then(setRow)
      .catch((e: Error) => setErr(e.message));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const resolve = (action: "match" | "create" | "dismiss", watchModelId?: string) => {
    if (!id) return;
    setBusy(action + (watchModelId ?? ""));
    setMsg(null);
    const body: Record<string, unknown> = { action };
    if (action === "match" && watchModelId) body.watch_model_id = watchModelId;
    fetch(apiUrl(`/api/watch-link-reviews/${id}/resolve`), {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<{ status: string }>;
      })
      .then((r) => {
        setMsg(`Done: ${r.status}`);
        router.push("/watch-review/");
      })
      .catch((e: Error) => setMsg(e.message))
      .finally(() => setBusy(null));
  };

  if (!id) {
    return <p className="text-destructive">Missing review id.</p>;
  }
  if (err) {
    return (
      <div className="space-y-2">
        <p className="text-red-300">{err}</p>
        <Button variant="outline" asChild>
          <Link href="/watch-review/">Back to queue</Link>
        </Button>
      </div>
    );
  }
  if (!row) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" className="mb-2 -ml-2" asChild>
          <Link href="/watch-review/">← Match queue</Link>
        </Button>
        <h1 className="text-2xl font-semibold">Resolve catalogue link</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Tier <strong>{row.tier ?? "—"}</strong>
          {row.confidence != null && row.confidence !== ""
            ? ` · confidence ${row.confidence}`
            : ""}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Listing</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="font-medium">{row.listing_title || row.ebay_item_id}</p>
          <p className="text-muted-foreground">eBay {row.ebay_item_id}</p>
          {row.listing_web_url ? (
            <Button variant="outline" size="sm" asChild>
              <a href={row.listing_web_url} target="_blank" rel="noopener noreferrer">
                Open on eBay
              </a>
            </Button>
          ) : null}
          <Button variant="outline" size="sm" asChild className="ml-2">
            <Link href={`/listings/detail/?id=${row.listing_id}`}>Open in WatchFinder</Link>
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="ml-2"
            disabled={busy !== null}
            onClick={() => {
              setBusy("not-interested");
              setMsg(null);
              fetch(apiUrl(`/api/watch-link-reviews/${id}/not-interested`), {
                method: "POST",
                headers: { Accept: "application/json" },
              })
                .then(async (res) => {
                  if (!res.ok) throw new Error(await res.text());
                  return res.json() as Promise<{ ebay_item_id: string }>;
                })
                .then((r) => {
                  router.push(`/not-interested/?q=${encodeURIComponent(r.ebay_item_id)}`);
                })
                .catch((e: Error) => setMsg(e.message))
                .finally(() => setBusy(null));
            }}
          >
            {busy === "not-interested" ? "…" : "Not interested"}
          </Button>
          {row.reason_codes?.length ? (
            <p className="pt-2 text-xs text-muted-foreground">
              Reasons: {row.reason_codes.join(", ")}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Probable catalog matches</CardTitle>
          <CardDescription>
            Scores are heuristic (reference, family, title vs model name). Pick one or create new.{" "}
            <strong>Observed</strong> ranges are from the watch database in <strong>£ GBP</strong> (min/max
            across linked listings and recorded sales for that catalog row).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {row.candidate_watch_models.length === 0 ? (
            <p className="text-sm text-muted-foreground">No similar rows — use Create new.</p>
          ) : (
            row.candidate_watch_models.map((m) => {
              const sc = row.candidate_scores[m.id];
              return (
                <div
                  key={m.id}
                  className="flex flex-col gap-2 rounded-md border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="text-sm">
                    <p className="font-medium">
                      {[m.brand, m.reference, m.model_family].filter(Boolean).join(" · ")}
                    </p>
                    {m.model_name ? (
                      <p className="text-xs text-muted-foreground">{m.model_name}</p>
                    ) : null}
                    <p className="text-xs text-muted-foreground tabular-nums">
                      catalog obs {money(m.observed_price_low, "GBP")} – {money(m.observed_price_high, "GBP")}
                      {sc != null ? ` · match score ${sc}` : ""}
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    disabled={busy !== null}
                    onClick={() => resolve("match", m.id)}
                  >
                    {busy === `match${m.id}` ? "…" : "Match to this"}
                  </Button>
                </div>
              );
            })
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => resolve("create")}
        >
          {busy === "create" ? "…" : "Create new catalog row from listing"}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="border-muted-foreground/40"
          disabled={busy !== null}
          onClick={() => resolve("dismiss")}
        >
          {busy === "dismiss" ? "…" : "Dismiss (no catalogue link)"}
        </Button>
      </div>
      {msg ? <p className="text-sm text-muted-foreground">{msg}</p> : null}
    </div>
  );
}
