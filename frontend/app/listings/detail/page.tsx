"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { fetchJson } from "@/lib/api";
import type { ListingDetail } from "@/lib/types";
import { money, dateShort } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ListingDetailPage() {
  return (
    <Suspense
      fallback={<p className="text-muted-foreground">Loading listing…</p>}
    >
      <DetailBody />
    </Suspense>
  );
}

function DetailBody() {
  const sp = useSearchParams();
  const id = sp.get("id");
  const [row, setRow] = useState<ListingDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setErr("Missing id query parameter.");
      return;
    }
    fetchJson<ListingDetail>(`/api/listings/${id}`)
      .then(setRow)
      .catch((e: Error) => setErr(e.message));
  }, [id]);

  if (!id) {
    return <p className="text-destructive">Missing listing id.</p>;
  }

  if (err) {
    return (
      <div className="space-y-2">
        <p className="text-red-300">{err}</p>
        <Button variant="outline" asChild>
          <Link href="/listings/">Back to listings</Link>
        </Button>
      </div>
    );
  }

  if (!row) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const latest = row.opportunity_scores?.[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Button variant="ghost" className="mb-2 -ml-2" asChild>
            <Link href="/listings/">← Listings</Link>
          </Button>
          <h1 className="text-2xl font-semibold leading-tight">
            {row.title || row.ebay_item_id}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            eBay {row.ebay_item_id} · {dateShort(row.last_seen_at)}
          </p>
        </div>
        {row.web_url && (
          <Button asChild>
            <a href={row.web_url} target="_blank" rel="noopener noreferrer">
              View on eBay
            </a>
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Listing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row k="Price" v={money(row.current_price, row.currency)} />
            <Row k="Shipping" v={money(row.shipping_price, row.currency)} />
            <Row k="Seller" v={row.seller_username || "—"} />
            <Row k="Condition" v={row.condition_description || "—"} />
            <Row k="Category" v={row.category_path || "—"} />
            <Row k="Active" v={row.is_active ? "yes" : "no"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Opportunity score</CardTitle>
            <CardDescription>
              Rule-based; tune economics in backend{" "}
              <code className="text-xs">services/scoring/constants.py</code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {latest ? (
              <>
                <Row
                  k="Potential profit"
                  v={money(latest.potential_profit, row.currency)}
                />
                <Row
                  k="Est. resale"
                  v={money(latest.estimated_resale, row.currency)}
                />
                <Row
                  k="Est. repair"
                  v={money(latest.estimated_repair_cost, row.currency)}
                />
                <Row
                  k="Max buy (rule)"
                  v={money(latest.advised_max_buy, row.currency)}
                />
                <Row
                  k="Confidence"
                  v={
                    latest.confidence != null
                      ? `${(Number(latest.confidence) * 100).toFixed(0)}%`
                      : "—"
                  }
                />
                <Row
                  k="Risk"
                  v={
                    latest.risk != null
                      ? `${(Number(latest.risk) * 100).toFixed(0)}%`
                      : "—"
                  }
                />
              </>
            ) : (
              <p className="text-muted-foreground">
                No score (no repair signals on this listing).
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {latest?.explanations?.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Why it was scored</CardTitle>
            <CardDescription>Transparent rule output.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
              {latest.explanations.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Repair signals</CardTitle>
        </CardHeader>
        <CardContent>
          {row.repair_signals?.length ? (
            <div className="flex flex-wrap gap-2">
              {row.repair_signals.map((s, i) => (
                <Badge key={i} variant="warn">
                  {s.signal_type}
                  {s.matched_text ? `: ${s.matched_text}` : ""}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">None.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Parsed attributes</CardTitle>
        </CardHeader>
        <CardContent>
          {row.parsed_attributes?.length ? (
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              {row.parsed_attributes.map((a) => (
                <div key={a.key} className="flex gap-2">
                  <dt className="font-medium text-muted-foreground">{a.key}</dt>
                  <dd>{a.value_text || "—"}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">None.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/50 py-1 last:border-0">
      <span className="text-muted-foreground">{k}</span>
      <span className="text-right">{v}</span>
    </div>
  );
}
