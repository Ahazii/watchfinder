"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiUrl, fetchJson } from "@/lib/api";
import type {
  ListingDetail,
  WatchModel,
  WatchModelListResponse,
} from "@/lib/types";
import { currencyInputLabelSuffix, money, dateShort } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

const SOURCE_OPTIONS = ["M", "I", "S", "R", "O", "H", "P"] as const;
const LISTING_TYPE_OPTIONS = [
  { value: "watch_complete", label: "Watch" },
  { value: "movement_only", label: "Movement only" },
  { value: "parts_other", label: "Other parts" },
  { value: "unknown", label: "Unknown" },
] as const;

export default function ListingDetailPage() {
  return (
    <Suspense
      fallback={<p className="text-muted-foreground">Loading listing…</p>}
    >
      <DetailBody />
    </Suspense>
  );
}

function Hint({ text }: { text: string }) {
  return (
    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{text}</p>
  );
}

function SourceSelect({
  value,
  onChange,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  id: string;
}) {
  return (
    <select
      id={id}
      className="h-9 rounded-md border border-border bg-background px-2 text-sm"
      value={value || "M"}
      onChange={(e) => onChange(e.target.value)}
    >
      {SOURCE_OPTIONS.map((x) => (
        <option key={x} value={x}>
          {x}
        </option>
      ))}
    </select>
  );
}

function DetailBody() {
  const sp = useSearchParams();
  const router = useRouter();
  const id = sp.get("id");
  const [row, setRow] = useState<ListingDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedOk, setSavedOk] = useState(false);

  const [modelFamily, setModelFamily] = useState("");
  const [modelFamilySrc, setModelFamilySrc] = useState("M");
  const [reference, setReference] = useState("");
  const [referenceSrc, setReferenceSrc] = useState("M");
  const [caliber, setCaliber] = useState("");
  const [caliberSrc, setCaliberSrc] = useState("M");
  const [repairSupp, setRepairSupp] = useState("");
  const [repairSuppSrc, setRepairSuppSrc] = useState("M");
  const [donor, setDonor] = useState("");
  const [donorSrc, setDonorSrc] = useState("M");
  const [salePrice, setSalePrice] = useState("");
  const [saleAt, setSaleAt] = useState("");
  const [saleSrc, setSaleSrc] = useState("M");
  const [notes, setNotes] = useState("");
  const [watchModelId, setWatchModelId] = useState("");
  const [listingType, setListingType] = useState<
    "watch_complete" | "movement_only" | "parts_other" | "unknown"
  >("unknown");
  const [catalog, setCatalog] = useState<WatchModel[]>([]);
  const [promoteBusy, setPromoteBusy] = useState(false);
  const [promoteErr, setPromoteErr] = useState<string | null>(null);
  const [promoteOk, setPromoteOk] = useState(false);
  const [refreshBusy, setRefreshBusy] = useState(false);
  const [notInterestedBusy, setNotInterestedBusy] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);
  const [reclassBusy, setReclassBusy] = useState(false);

  useEffect(() => {
    fetchJson<WatchModelListResponse>("/api/watch-models?limit=500")
      .then((r) => setCatalog(r.items))
      .catch(() => setCatalog([]));
  }, []);

  const applyDetail = useCallback((d: ListingDetail) => {
    setRow(d);
    setModelFamily(d.model_family?.value ?? "");
    setModelFamilySrc(d.model_family?.source || "M");
    setReference(d.reference?.value ?? "");
    setReferenceSrc(d.reference?.source || "M");
    setCaliber(d.caliber?.value ?? "");
    setCaliberSrc(d.caliber?.source || "M");
    setRepairSupp(
      d.repair_supplement?.amount != null ? String(d.repair_supplement.amount) : "",
    );
    setRepairSuppSrc(d.repair_supplement?.source || "M");
    setDonor(d.donor_cost?.amount != null ? String(d.donor_cost.amount) : "");
    setDonorSrc(d.donor_cost?.source || "M");
    setSalePrice(
      d.recorded_sale?.price != null ? String(d.recorded_sale.price) : "",
    );
    setSaleAt(
      d.recorded_sale?.recorded_at
        ? d.recorded_sale.recorded_at.slice(0, 16)
        : "",
    );
    setSaleSrc(d.recorded_sale?.source || "M");
    setNotes(d.notes ?? "");
    setWatchModelId(d.watch_model_id ?? "");
    setListingType(d.listing_type ?? "unknown");
    setSavedOk(false);
  }, []);

  const load = useCallback((): Promise<void> => {
    if (!id) return Promise.resolve();
    setErr(null);
    return fetchJson<ListingDetail>(`/api/listings/${id}`)
      .then(applyDetail)
      .catch((e: Error) => {
        setErr(e.message);
      });
  }, [id, applyDetail]);

  const refreshFromEbay = () => {
    if (!id) return;
    setRefreshBusy(true);
    setRefreshMsg(null);
    fetch(apiUrl(`/api/listings/${id}/refresh-from-ebay`), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<ListingDetail>;
      })
      .then((d) => {
        applyDetail(d);
        setRefreshMsg(
          d.is_active === false
            ? "eBay has no live listing for this id — marked inactive (hidden from default lists)."
            : "Updated from eBay (getItem).",
        );
      })
      .catch((e: Error) => setRefreshMsg(e.message))
      .finally(() => setRefreshBusy(false));
  };

  const markNotInterested = () => {
    if (!id) return;
    setNotInterestedBusy(true);
    setRefreshMsg(null);
    fetch(apiUrl(`/api/listings/${id}/not-interested`), {
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
      .catch((e: Error) => setRefreshMsg(e.message))
      .finally(() => setNotInterestedBusy(false));
  };

  useEffect(() => {
    load();
  }, [load]);

  const save = () => {
    if (!id) return;
    setSaveErr(null);
    setSaving(true);
    setSavedOk(false);
    const num = (s: string) => {
      const t = s.trim();
      if (!t) return null;
      const n = Number(t);
      return Number.isFinite(n) ? n : null;
    };
    const body: Record<string, unknown> = {
      watch_model_id: watchModelId.trim() ? watchModelId.trim() : null,
      model_family: modelFamily.trim() || null,
      model_family_source: modelFamilySrc,
      reference_text: reference.trim() || null,
      reference_source: referenceSrc,
      caliber_text: caliber.trim() || null,
      caliber_source: caliberSrc,
      repair_supplement: num(repairSupp),
      repair_supplement_source: repairSuppSrc,
      donor_cost: num(donor),
      donor_source: donorSrc,
      recorded_sale_price: num(salePrice),
      recorded_sale_source: saleSrc,
      notes: notes.trim() || null,
    };
    const prevType = row?.listing_type ?? "unknown";
    if (listingType !== prevType) {
      body.listing_type = listingType;
    }
    if (saleAt.trim()) {
      const iso = new Date(saleAt).toISOString();
      body.recorded_sale_at = iso;
    } else {
      body.recorded_sale_at = null;
    }

    fetch(apiUrl(`/api/listings/${id}`), {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<ListingDetail>;
      })
      .then((d) => {
        setRow(d);
        setSavedOk(true);
        setModelFamily(d.model_family?.value ?? "");
        setModelFamilySrc(d.model_family?.source || "M");
        setReference(d.reference?.value ?? "");
        setReferenceSrc(d.reference?.source || "M");
        setCaliber(d.caliber?.value ?? "");
        setCaliberSrc(d.caliber?.source || "M");
        setRepairSupp(
          d.repair_supplement?.amount != null ? String(d.repair_supplement.amount) : "",
        );
        setRepairSuppSrc(d.repair_supplement?.source || "M");
        setDonor(d.donor_cost?.amount != null ? String(d.donor_cost.amount) : "");
        setDonorSrc(d.donor_cost?.source || "M");
        setSalePrice(
          d.recorded_sale?.price != null ? String(d.recorded_sale.price) : "",
        );
        setSaleAt(
          d.recorded_sale?.recorded_at
            ? d.recorded_sale.recorded_at.slice(0, 16)
            : "",
        );
        setSaleSrc(d.recorded_sale?.source || "M");
        setNotes(d.notes ?? "");
        setWatchModelId(d.watch_model_id ?? "");
        setListingType(d.listing_type ?? "unknown");
      })
      .catch((e: Error) => setSaveErr(e.message))
      .finally(() => setSaving(false));
  };

  const reclassifyListingTypeAuto = () => {
    if (!id) return;
    setSaveErr(null);
    setReclassBusy(true);
    fetch(apiUrl(`/api/listings/${id}`), {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ listing_type_source: "auto" }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<ListingDetail>;
      })
      .then((d) => {
        applyDetail(d);
        setSavedOk(true);
      })
      .catch((e: Error) => setSaveErr(e.message))
      .finally(() => setReclassBusy(false));
  };

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
  const g = row.field_guidance || {};
  const listCur = row.currency?.trim() || "GBP";
  const curSuf = currencyInputLabelSuffix(listCur);

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
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>
              eBay {row.ebay_item_id} · last seen {dateShort(row.last_seen_at)}
            </span>
            {row.is_active === false ? (
              <Badge variant="secondary" className="border-amber-900/50 text-amber-200">
                Inactive
              </Badge>
            ) : (
              <Badge variant="outline" className="border-emerald-900/40 text-emerald-200/90">
                Active
              </Badge>
            )}
          </p>
          <p className="mt-1 text-sm">
            <span className="text-muted-foreground">Parsed brand</span>{" "}
            {row.brand?.value || "—"}{" "}
            {row.brand?.source ? (
              <Badge variant="secondary" className="ml-1 text-xs">
                {row.brand.source}
              </Badge>
            ) : null}
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted-foreground">Listing type</span>{" "}
            <Badge variant="secondary" className="text-xs">
              {LISTING_TYPE_OPTIONS.find((x) => x.value === (row.listing_type ?? "unknown"))
                ?.label ?? "Unknown"}
            </Badge>
            <Badge variant="outline" className="text-xs">
              {row.listing_type_source === "manual" ? "Manual" : "Auto"}
            </Badge>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            asChild={Boolean(row.web_url)}
            disabled={!row.web_url}
            className="min-w-[132px]"
          >
            {row.web_url ? (
              <a href={row.web_url} target="_blank" rel="noopener noreferrer">
                View on eBay
              </a>
            ) : (
              <span>View on eBay</span>
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="min-w-[150px]"
            disabled={refreshBusy}
            title='Refresh from eBay and mark inactive only when page shows "We looked everywhere."'
            onClick={refreshFromEbay}
          >
            {refreshBusy ? "Refreshing…" : "Refresh from eBay"}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="min-w-[132px]"
            disabled={notInterestedBusy}
            onClick={markNotInterested}
            title="Remove this listing and block the eBay item id from future ingest"
          >
            {notInterestedBusy ? "Working…" : "Not interested"}
          </Button>
        </div>
      </div>
      {refreshMsg ? (
        <p className="text-sm text-muted-foreground">{refreshMsg}</p>
      ) : null}

      {row.watch_link_review_pending ? (
        <Card className="border-amber-900/40 bg-amber-950/20">
          <CardHeader>
            <CardTitle className="text-amber-200">Catalogue review pending</CardTitle>
            <CardDescription className="text-amber-200/80">
              This listing is in the match queue (review mode). Open the queue to pick a catalog row
              or create one.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link
                href={`/watch-review/detail/?id=${row.watch_link_review_pending.id}`}
              >
                Open in match queue
              </Link>
            </Button>
            <span className="ml-3 text-xs text-muted-foreground">
              {row.watch_link_review_pending.candidate_count} candidate(s) · tier{" "}
              {row.watch_link_review_pending.tier ?? "—"}
            </span>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Watch catalog link</CardTitle>
          <CardDescription>
            New and updated listings try to match the catalog first, then <strong>create</strong> a
            catalog row when brand + reference (or brand + family) are known. Use the button below
            to run that on demand, or pick a row manually. <strong>Catalog obs</strong> is the linked
            watch model’s observed price band in <strong>£ GBP</strong> (from all listings/sales tied
            to that catalog row), not this listing’s currency alone.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {row.watch_model ? (
            <p>
              Linked:{" "}
              <Link
                className="text-primary underline"
                href={`/watch-models/detail/?id=${row.watch_model.id}`}
              >
                {[row.watch_model.brand, row.watch_model.reference, row.watch_model.model_family]
                  .filter(Boolean)
                  .join(" · ")}
              </Link>
              <span className="ml-2 text-muted-foreground tabular-nums">
                catalog obs {money(row.watch_model.observed_price_low, "GBP")} –{" "}
                {money(row.watch_model.observed_price_high, "GBP")}
              </span>
            </p>
          ) : (
            <p className="text-muted-foreground">
              Not linked yet. Save after ingest, or pick a model below.
            </p>
          )}
          <div>
            <label className="font-medium" htmlFor="wm-sel">
              Linked model
            </label>
            <select
              id="wm-sel"
              className="mt-1 flex h-9 w-full max-w-xl rounded-md border border-border bg-background px-2 text-sm"
              value={watchModelId}
              onChange={(e) => setWatchModelId(e.target.value)}
            >
              <option value="">— None (clear / auto-link on save) —</option>
              {catalog.map((m) => (
                <option key={m.id} value={m.id}>
                  {[m.brand, m.reference, m.model_family].filter(Boolean).join(" · ") || m.id}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={!id || promoteBusy}
              onClick={async () => {
                if (!id) return;
                setPromoteErr(null);
                setPromoteOk(false);
                setPromoteBusy(true);
                try {
                  const res = await fetch(apiUrl(`/api/listings/${id}/promote-watch-catalog`), {
                    method: "POST",
                    headers: { Accept: "application/json" },
                  });
                  if (!res.ok) throw new Error(await res.text());
                  await res.json();
                  setPromoteOk(true);
                  await load();
                  const cat = await fetchJson<WatchModelListResponse>(
                    "/api/watch-models?limit=500",
                  );
                  setCatalog(cat.items);
                } catch (e) {
                  setPromoteErr((e as Error).message);
                } finally {
                  setPromoteBusy(false);
                }
              }}
            >
              {promoteBusy ? "Working…" : "Save to watch database"}
            </Button>
            <span className="text-xs text-muted-foreground">
              Match an existing row or create one from this listing&apos;s brand / reference / family.
            </span>
          </div>
          {promoteErr ? <p className="text-xs text-red-400">{promoteErr}</p> : null}
          {promoteOk ? (
            <p className="text-xs text-green-600 dark:text-green-400">Catalog updated.</p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Internal comps</CardTitle>
          <CardDescription>
            {g.comps} Bands use prices already in your database: recorded sales and other active listings
            with the same parsed brand. Figures in the two boxes below are shown in this listing’s eBay
            currency (<strong>{listCur}</strong>) with the usual money symbols.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 text-sm">
          <div className="rounded-md border border-border p-3">
            <p className="font-medium">Recorded sales</p>
            <p className="text-xs text-muted-foreground">
              {row.comp_sales.label} Prices you (or the pipeline) saved as sold outcomes; percentiles help
              judge typical realised values in <strong>{listCur}</strong>.
            </p>
            <p className="mt-2 tabular-nums">
              n={row.comp_sales.count}
              {row.comp_sales.count > 0 ? (
                <>
                  {" "}
                  · p25 {money(row.comp_sales.p25, row.currency)} · p75{" "}
                  {money(row.comp_sales.p75, row.currency)}
                </>
              ) : null}
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="font-medium">Active asking (your DB)</p>
            <p className="text-xs text-muted-foreground">
              {row.comp_asking.label} Current <strong>Buy It Now / asking</strong> prices from other live
              listings in your ingest that share the same brand — rough market spread in <strong>
                {listCur}
              </strong>
              .
            </p>
            <p className="mt-2 tabular-nums">
              n={row.comp_asking.count}
              {row.comp_asking.count > 0 ? (
                <>
                  {" "}
                  · p25 {money(row.comp_asking.p25, row.currency)} · p75{" "}
                  {money(row.comp_asking.p75, row.currency)}
                </>
              ) : null}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your valuation inputs</CardTitle>
          <CardDescription>
            Edit and save. Source letters are stored per field (see legend below). Enter repair, donor, and
            recorded sale amounts in the same currency as this listing{curSuf} — eBay uses code{" "}
            <strong>{listCur}</strong> for this row.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label className="text-sm font-medium" htmlFor="mf">
                Model family
              </label>
              <Input
                id="mf"
                value={modelFamily}
                onChange={(e) => setModelFamily(e.target.value)}
                className="mt-1"
              />
              <Hint text={g.model_family} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-muted-foreground" htmlFor="mf-s">
                Src
              </label>
              <SourceSelect
                id="mf-s"
                value={modelFamilySrc}
                onChange={setModelFamilySrc}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label className="text-sm font-medium" htmlFor="ref">
                Reference
              </label>
              <Input
                id="ref"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                className="mt-1"
              />
              <Hint text={g.reference} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-muted-foreground" htmlFor="ref-s">
                Src
              </label>
              <SourceSelect
                id="ref-s"
                value={referenceSrc}
                onChange={setReferenceSrc}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label className="text-sm font-medium" htmlFor="cal">
                Caliber / movement
              </label>
              <Input
                id="cal"
                value={caliber}
                onChange={(e) => setCaliber(e.target.value)}
                className="mt-1"
              />
              <Hint text={g.caliber} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-muted-foreground" htmlFor="cal-s">
                Src
              </label>
              <SourceSelect
                id="cal-s"
                value={caliberSrc}
                onChange={setCaliberSrc}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label className="text-sm font-medium" htmlFor="rs">
                Repair add-on (manual / historical)
                {curSuf}
              </label>
              <Input
                id="rs"
                type="number"
                step="0.01"
                value={repairSupp}
                onChange={(e) => setRepairSupp(e.target.value)}
                className="mt-1"
              />
              <Hint text={g.repair_supplement} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-muted-foreground" htmlFor="rs-s">
                Src
              </label>
              <SourceSelect
                id="rs-s"
                value={repairSuppSrc}
                onChange={setRepairSuppSrc}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label className="text-sm font-medium" htmlFor="dn">
                Donor / parts cost
                {curSuf}
              </label>
              <Input
                id="dn"
                type="number"
                step="0.01"
                value={donor}
                onChange={(e) => setDonor(e.target.value)}
                className="mt-1"
              />
              <Hint text={g.donor_cost} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-muted-foreground" htmlFor="dn-s">
                Src
              </label>
              <SourceSelect id="dn-s" value={donorSrc} onChange={setDonorSrc} />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
            <div>
              <label className="text-sm font-medium" htmlFor="sp">
                Recorded sale price
                {curSuf}
              </label>
              <Input
                id="sp"
                type="number"
                step="0.01"
                value={salePrice}
                onChange={(e) => setSalePrice(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium" htmlFor="sa">
                Sale time
              </label>
              <Input
                id="sa"
                type="datetime-local"
                value={saleAt}
                onChange={(e) => setSaleAt(e.target.value)}
                className="mt-1"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-muted-foreground" htmlFor="ss">
                Src
              </label>
              <SourceSelect id="ss" value={saleSrc} onChange={setSaleSrc} />
            </div>
          </div>
          <Hint text={g.recorded_sale} />

          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[200px] flex-1">
              <label className="text-sm font-medium" htmlFor="listing-type">
                Listing type
              </label>
              <select
                id="listing-type"
                className="mt-1 flex h-9 w-full max-w-sm rounded-md border border-border bg-background px-2 text-sm"
                value={listingType}
                onChange={(e) =>
                  setListingType(
                    e.target.value as
                      | "watch_complete"
                      | "movement_only"
                      | "parts_other"
                      | "unknown",
                  )
                }
              >
                {LISTING_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <Hint text="Changing the value and saving marks the type as manual. Other saves leave auto/manual unchanged." />
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mb-0.5"
              disabled={reclassBusy || row.listing_type_source !== "manual"}
              title="Clear manual lock and re-run automatic classification"
              onClick={reclassifyListingTypeAuto}
            >
              {reclassBusy ? "Working…" : "Re-classify automatically"}
            </Button>
          </div>

          <div>
            <label className="text-sm font-medium" htmlFor="notes">
              Notes
            </label>
            <textarea
              id="notes"
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-1 flex w-full rounded-md border border-border bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            />
            <Hint text={g.notes} />
          </div>

          {saveErr ? <p className="text-sm text-red-400">{saveErr}</p> : null}
          {savedOk ? (
            <p className="text-sm text-green-600 dark:text-green-400">Saved.</p>
          ) : null}
          <Button type="button" disabled={saving} onClick={save}>
            {saving ? "Saving…" : "Save changes"}
          </Button>

          <div className="border-t border-border pt-4">
            <p className="text-sm font-medium">Source letters</p>
            <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
              {Object.entries(row.source_legend || {}).map(([k, v]) => (
                <li key={k}>
                  <strong>{k}</strong> — {v}
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Listing</CardTitle>
            <CardDescription>
              As last ingested or refreshed from eBay. <strong>Price</strong> and <strong>shipping</strong>{" "}
              are in the listing’s marketplace currency (<strong>{listCur}</strong>).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row k={`Price (${listCur})`} v={money(row.current_price, row.currency)} />
            <Row k={`Shipping (${listCur})`} v={money(row.shipping_price, row.currency)} />
            <Row k="Seller" v={row.seller_username || "—"} />
            <Row k="Condition" v={row.condition_description || "—"} />
            <Row k="Category" v={row.category_path || "—"} />
            <Row k="Sale type" v={row.buying_options?.length ? row.buying_options.join(", ") : "—"} />
            <Row k="Listing ends" v={dateShort(row.listing_ended_at)} />
            <Row k="Active" v={row.is_active ? "yes" : "no"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Opportunity score</CardTitle>
            <CardDescription>
              Rule-based core + your repair add-on and donor cost. All monetary lines below use this
              listing’s eBay currency (<strong>{listCur}</strong>) so they stay comparable to{" "}
              <strong>Price</strong> above.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {latest ? (
              <>
                <Row
                  k={`Potential profit (${listCur})`}
                  v={money(latest.potential_profit, row.currency)}
                />
                <Row
                  k={`Est. resale (${listCur})`}
                  v={money(latest.estimated_resale, row.currency)}
                />
                <Row
                  k={`Est. repair (total) (${listCur})`}
                  v={money(latest.estimated_repair_cost, row.currency)}
                />
                <Row
                  k={`Max buy (rule) (${listCur})`}
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
            <CardDescription>
              Human-readable reasons the scorer produced this result (which rules fired, rough logic). Not
              financial advice.
            </CardDescription>
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
            <CardDescription>
              Keywords and phrases detected in the title or parsed fields that suggest work may be needed.
            </CardDescription>
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
            <CardDescription>
              Structured key/value pairs extracted from the listing text for matching and display.
            </CardDescription>
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
