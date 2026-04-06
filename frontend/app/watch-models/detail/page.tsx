"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiUrl, fetchJson, mediaUrl } from "@/lib/api";
import type {
  WatchBaseImportResult,
  WatchBasePriceHistory,
  WatchModel,
  WatchbaseSearchResponse,
} from "@/lib/types";
import { currencyInputLabelSuffix, money } from "@/lib/format";
import {
  watchbaseGoogleSearchUrl,
  watchbaseGoogleSiteSearchUrl,
  watchbaseGuessUrl,
} from "@/lib/watchbase";
import { ListingThumb } from "@/components/listing-thumb";
import { TableThumbSizeSelect } from "@/components/table-thumb-size-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  TABLE_THUMB_STORAGE,
  WATCHBASE_FIND_PREVIEW_MAX_CLASS,
  usePersistedTableThumbSize,
} from "@/lib/table-thumb-sizes";

export default function WatchModelDetailPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
      <DetailBody />
    </Suspense>
  );
}

function DetailBody() {
  const sp = useSearchParams();
  const router = useRouter();
  const id = sp.get("id");
  const isNew = !id;

  const [err, setErr] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [brand, setBrand] = useState("");
  const [modelFamily, setModelFamily] = useState("");
  const [modelName, setModelName] = useState("");
  const [reference, setReference] = useState("");
  const [caliber, setCaliber] = useState("");
  const [imageLines, setImageLines] = useState("");
  const [prodStart, setProdStart] = useState("");
  const [prodEnd, setProdEnd] = useState("");
  const [description, setDescription] = useState("");
  const [manualLow, setManualLow] = useState("");
  const [manualHigh, setManualHigh] = useState("");
  const [observedLow, setObservedLow] = useState<string | number | null>(null);
  const [observedHigh, setObservedHigh] = useState<string | number | null>(null);
  const [referenceUrl, setReferenceUrl] = useState("");
  const [specCaseMaterial, setSpecCaseMaterial] = useState("");
  const [specBezel, setSpecBezel] = useState("");
  const [specCrystal, setSpecCrystal] = useState("");
  const [specCaseBack, setSpecCaseBack] = useState("");
  const [specCaseDia, setSpecCaseDia] = useState("");
  const [specCaseH, setSpecCaseH] = useState("");
  const [specLug, setSpecLug] = useState("");
  const [specWr, setSpecWr] = useState("");
  const [specDialColor, setSpecDialColor] = useState("");
  const [specDialMat, setSpecDialMat] = useState("");
  const [specIdxHands, setSpecIdxHands] = useState("");
  const [linkedEbayUrls, setLinkedEbayUrls] = useState<string[]>([]);
  const [importBusy, setImportBusy] = useState(false);
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const [importDetail, setImportDetail] = useState<WatchBaseImportResult | null>(null);
  const [extPrices, setExtPrices] = useState<WatchBasePriceHistory | null>(null);
  const [findModalOpen, setFindModalOpen] = useState(false);
  const [modalPos, setModalPos] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  } | null>(null);
  const [findSearchDetail, setFindSearchDetail] = useState("");
  const [findPastedUrl, setFindPastedUrl] = useState("");
  const [findWbSearchBusy, setFindWbSearchBusy] = useState(false);
  const [findWbSearchErr, setFindWbSearchErr] = useState<string | null>(null);
  const [findWbHits, setFindWbHits] = useState<WatchbaseSearchResponse["items"] | null>(null);

  const {
    sizeId: wbFindThumbId,
    setSizeId: setWbFindThumbId,
    sizeClass: wbFindThumbClass,
  } = usePersistedTableThumbSize(TABLE_THUMB_STORAGE.watchbaseFind);
  const wbFindPreviewMaxClass = WATCHBASE_FIND_PREVIEW_MAX_CLASS[wbFindThumbId];

  const closeFindModal = useCallback(() => {
    setFindModalOpen(false);
    setFindPastedUrl("");
    setFindWbHits(null);
    setFindWbSearchErr(null);
  }, []);

  useEffect(() => {
    if (!findModalOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeFindModal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [findModalOpen, closeFindModal]);

  useEffect(() => {
    if (!findModalOpen) return;
    const onMove = (e: MouseEvent) => {
      const d = dragRef.current;
      if (!d) return;
      setModalPos({
        x: d.origX + e.clientX - d.startX,
        y: d.origY + e.clientY - d.startY,
      });
    };
    const onUp = () => {
      dragRef.current = null;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [findModalOpen]);

  const applyModel = useCallback((m: WatchModel) => {
    setBrand(m.brand ?? "");
    setModelFamily(m.model_family ?? "");
    setModelName(m.model_name ?? "");
    setReference(m.reference ?? "");
    setCaliber(m.caliber ?? "");
    setImageLines((m.image_urls ?? []).join("\n"));
    setProdStart(m.production_start?.slice(0, 10) ?? "");
    setProdEnd(m.production_end?.slice(0, 10) ?? "");
    setDescription(m.description ?? "");
    setManualLow(m.manual_price_low != null ? String(m.manual_price_low) : "");
    setManualHigh(m.manual_price_high != null ? String(m.manual_price_high) : "");
    setObservedLow(m.observed_price_low ?? null);
    setObservedHigh(m.observed_price_high ?? null);
    setReferenceUrl(m.reference_url ?? "");
    setSpecCaseMaterial(m.spec_case_material ?? "");
    setSpecBezel(m.spec_bezel ?? "");
    setSpecCrystal(m.spec_crystal ?? "");
    setSpecCaseBack(m.spec_case_back ?? "");
    setSpecCaseDia(
      m.spec_case_diameter_mm != null ? String(m.spec_case_diameter_mm) : "",
    );
    setSpecCaseH(m.spec_case_height_mm != null ? String(m.spec_case_height_mm) : "");
    setSpecLug(m.spec_lug_width_mm != null ? String(m.spec_lug_width_mm) : "");
    setSpecWr(
      m.spec_water_resistance_m != null ? String(m.spec_water_resistance_m) : "",
    );
    setSpecDialColor(m.spec_dial_color ?? "");
    setSpecDialMat(m.spec_dial_material ?? "");
    setSpecIdxHands(m.spec_indexes_hands ?? "");
    setExtPrices(m.external_price_history ?? null);
    setLinkedEbayUrls(m.linked_ebay_urls ?? []);
  }, []);

  useEffect(() => {
    if (isNew) {
      applyModel({
        id: "",
        brand: "",
        model_family: null,
        model_name: null,
        reference: null,
        caliber: null,
        image_urls: null,
        production_start: null,
        production_end: null,
        description: null,
        manual_price_low: null,
        manual_price_high: null,
        observed_price_low: null,
        observed_price_high: null,
        reference_url: null,
        spec_case_material: null,
        spec_bezel: null,
        spec_crystal: null,
        spec_case_back: null,
        spec_case_diameter_mm: null,
        spec_case_height_mm: null,
        spec_lug_width_mm: null,
        spec_water_resistance_m: null,
        spec_dial_color: null,
        spec_dial_material: null,
        spec_indexes_hands: null,
        external_price_history: null,
        watchbase_imported_at: null,
        linked_ebay_urls: [],
      });
      setErr(null);
      return;
    }
    setErr(null);
    fetchJson<WatchModel>(`/api/watch-models/${id}`)
      .then(applyModel)
      .catch((e: Error) => setErr(e.message));
  }, [id, isNew, applyModel]);

  const num = (s: string) => {
    const t = s.trim();
    if (!t) return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  };

  const dateOrNull = (s: string) => {
    const t = s.trim();
    return t || null;
  };

  const buildPayload = () => {
    const urls = imageLines
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    return {
      brand: brand.trim(),
      model_family: modelFamily.trim() || null,
      model_name: modelName.trim() || null,
      reference: reference.trim() || null,
      caliber: caliber.trim() || null,
      image_urls: urls.length ? urls : null,
      production_start: dateOrNull(prodStart),
      production_end: dateOrNull(prodEnd),
      description: description.trim() || null,
      manual_price_low: num(manualLow),
      manual_price_high: num(manualHigh),
      reference_url: referenceUrl.trim() || null,
      spec_case_material: specCaseMaterial.trim() || null,
      spec_bezel: specBezel.trim() || null,
      spec_crystal: specCrystal.trim() || null,
      spec_case_back: specCaseBack.trim() || null,
      spec_case_diameter_mm: num(specCaseDia),
      spec_case_height_mm: num(specCaseH),
      spec_lug_width_mm: num(specLug),
      spec_water_resistance_m: num(specWr),
      spec_dial_color: specDialColor.trim() || null,
      spec_dial_material: specDialMat.trim() || null,
      spec_indexes_hands: specIdxHands.trim() || null,
    };
  };

  /**
   * WatchBase import. `urlOverride` undefined → use Reference URL field (may be null so backend can guess
   * from brand / family / reference). `urlOverride` set (wizard) → must be non-empty WatchBase URL.
   */
  const runWatchbaseImport = (urlOverride?: string | null, onSuccess?: () => void) => {
    if (!id || isNew) return;
    let refUrl: string | null;
    if (urlOverride !== undefined) {
      refUrl = (urlOverride && urlOverride.trim()) || null;
      if (!refUrl) {
        setImportMsg("Paste the WatchBase watch page URL from the address bar, then confirm import.");
        return;
      }
    } else {
      refUrl = referenceUrl.trim() || null;
    }
    setImportBusy(true);
    setImportMsg(null);
    setImportDetail(null);
    fetch(apiUrl(`/api/watch-models/${id}/import-watchbase`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        reference_url: refUrl,
      }),
    })
      .then(async (res) => {
        const text = await res.text();
        if (!res.ok) {
          try {
            const j = JSON.parse(text) as { detail?: string | unknown };
            const d = j.detail;
            throw new Error(
              typeof d === "string" ? d : Array.isArray(d) ? JSON.stringify(d) : text,
            );
          } catch {
            throw new Error(text || res.statusText);
          }
        }
        return JSON.parse(text) as WatchBaseImportResult;
      })
      .then((r) => {
        setImportDetail(r);
        setImportMsg(
          `Imported ${r.price_points} price point(s). Updated: ${r.fields_updated.join(", ")}.`,
        );
        return fetchJson<WatchModel>(`/api/watch-models/${id}`);
      })
      .then((m) => {
        applyModel(m);
        onSuccess?.();
      })
      .catch((e: Error) => setImportMsg(e.message))
      .finally(() => setImportBusy(false));
  };

  const onFindModalDragMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      origX: modalPos.x,
      origY: modalPos.y,
    };
  };

  const openFindWatchbaseWizard = () => {
    const seed = reference.trim() || brand.trim() || "";
    setFindSearchDetail(seed);
    setFindPastedUrl("");
    setFindWbHits(null);
    setFindWbSearchErr(null);
    setImportMsg(null);
    if (typeof window !== "undefined") {
      const panelW = Math.min(512, window.innerWidth - 32);
      setModalPos({
        x: Math.max(8, Math.round((window.innerWidth - panelW) / 2)),
        y: Math.max(8, Math.round(window.innerHeight * 0.06)),
      });
    }
    setFindModalOpen(true);
  };

  const findGoogleUrl = watchbaseGoogleSiteSearchUrl(findSearchDetail);

  const searchWatchbaseOnSite = () => {
    const q = findSearchDetail.trim();
    if (!q) return;
    setFindWbSearchBusy(true);
    setFindWbSearchErr(null);
    setFindWbHits(null);
    setFindPastedUrl("");
    fetchJson<WatchbaseSearchResponse>(`/api/watchbase/search?q=${encodeURIComponent(q)}`)
      .then((res) => {
        setFindWbHits(res.items);
        if (res.items.length === 1) {
          setFindPastedUrl(res.items[0].url);
        }
      })
      .catch((e: Error) => setFindWbSearchErr(e.message))
      .finally(() => setFindWbSearchBusy(false));
  };

  const save = () => {
    if (!brand.trim()) {
      setSaveErr("Brand is required.");
      return;
    }
    setSaveErr(null);
    setSaving(true);
    const payload = buildPayload();

    if (isNew) {
      fetch(apiUrl("/api/watch-models"), {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
        .then(async (res) => {
          if (!res.ok) throw new Error(await res.text());
          return res.json() as Promise<WatchModel>;
        })
        .then((m) => router.replace(`/watch-models/detail/?id=${m.id}`))
        .catch((e: Error) => setSaveErr(e.message))
        .finally(() => setSaving(false));
      return;
    }

    fetch(apiUrl(`/api/watch-models/${id}`), {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<WatchModel>;
      })
      .then(applyModel)
      .catch((e: Error) => setSaveErr(e.message))
      .finally(() => setSaving(false));
  };

  const remove = () => {
    if (!id || isNew) return;
    if (!window.confirm("Delete this watch model? Linked listings will be unlinked.")) return;
    setDeleting(true);
    setSaveErr(null);
    fetch(apiUrl(`/api/watch-models/${id}`), { method: "DELETE" })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
      })
      .then(() => router.push("/watch-models/"))
      .catch((e: Error) => setSaveErr(e.message))
      .finally(() => setDeleting(false));
  };

  const previewImageUrls = useMemo(
    () => imageLines.split(/\r?\n/).map((l) => l.trim()).filter(Boolean),
    [imageLines],
  );
  const photoAlt = [brand, reference, modelFamily].filter(Boolean).join(" · ") || "Watch";

  if (err) {
    return (
      <div className="space-y-2">
        <p className="text-red-300">{err}</p>
        <Button variant="outline" asChild>
          <Link href="/watch-models/">Back to watch database</Link>
        </Button>
      </div>
    );
  }

  const wbGuess = watchbaseGuessUrl(brand, modelFamily, reference);
  const wbGoogle = watchbaseGoogleSearchUrl(brand, reference);
  const selectedWbHit = findWbHits?.find((h) => h.url === findPastedUrl);

  return (
    <div className="space-y-6">
      {findModalOpen ? (
        <>
          {/* Dim only; pointer-events-none so you can click the page behind without closing. */}
          <div
            className="pointer-events-none fixed inset-0 z-40 bg-black/50"
            aria-hidden
          />
          <div
            role="dialog"
            aria-modal="false"
            aria-labelledby="find-watchbase-title"
            className="fixed z-50 w-[calc(100%-2rem)] max-w-xl overflow-hidden rounded-lg border border-border bg-background text-foreground shadow-xl"
            style={{ left: modalPos.x, top: modalPos.y }}
          >
            <div
              className="flex cursor-grab select-none items-start gap-2 border-b border-border bg-muted/40 px-4 py-3 active:cursor-grabbing"
              onMouseDown={onFindModalDragMouseDown}
            >
              <div className="min-w-0 flex-1">
                <h2 id="find-watchbase-title" className="text-lg font-semibold leading-tight">
                  Find watch on WatchBase
                </h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Drag this bar to move. Click the page behind to edit the form — this panel stays open. Escape
                  or Cancel closes it.
                </p>
              </div>
            </div>
            <div className="max-h-[min(78vh,640px)] overflow-y-auto p-6 pt-4">
              <p className="text-sm text-muted-foreground">
                Search uses WatchBase’s filter API. Pick a result (thumbnail below when selected), then confirm
                import — same as <strong>Import from WatchBase</strong>. Or use <strong>Open Google</strong> /
                paste a URL.
              </p>
              <div className="mt-3 flex flex-wrap items-center justify-end gap-2 border-b border-border pb-3">
                <TableThumbSizeSelect
                  id="watchbase-find-thumb-size"
                  compact
                  value={wbFindThumbId}
                  onChange={setWbFindThumbId}
                />
              </div>
              <div className="mt-4 space-y-2">
                <label className="text-sm font-medium" htmlFor="find-detail">
                  Search detail
                </label>
                <Input
                  id="find-detail"
                  className="font-mono text-xs"
                  placeholder="e.g. 210.30.42.20.01.001 or Omega 210.30"
                  value={findSearchDetail}
                  onChange={(e) => setFindSearchDetail(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      searchWatchbaseOnSite();
                    }
                  }}
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  disabled={findWbSearchBusy || !findSearchDetail.trim()}
                  onClick={searchWatchbaseOnSite}
                >
                  {findWbSearchBusy ? "Searching…" : "Search WatchBase"}
                </Button>
                {findGoogleUrl ? (
                  <Button variant="outline" size="sm" asChild>
                    <a href={findGoogleUrl} target="_blank" rel="noopener noreferrer">
                      Open Google (site:watchbase.com)
                    </a>
                  </Button>
                ) : (
                  <Button type="button" variant="outline" size="sm" disabled title="Type a search detail first">
                    Open Google (site:watchbase.com)
                  </Button>
                )}
              </div>
              {findWbSearchErr ? (
                <p className="mt-3 text-sm text-red-400">{findWbSearchErr}</p>
              ) : null}
              {findWbHits && findWbHits.length > 0 ? (
                <div className="mt-4">
                  <p className="mb-2 text-sm font-medium">Results — click one to select</p>
                  <ul className="max-h-[min(50vh,22rem)] space-y-1 overflow-y-auto rounded-md border border-border p-2 text-sm">
                    {findWbHits.map((h) => (
                      <li key={h.url}>
                        <button
                          type="button"
                          className={`flex w-full items-start gap-2 rounded px-2 py-1.5 text-left hover:bg-muted ${
                            findPastedUrl === h.url ? "bg-muted ring-1 ring-primary" : ""
                          }`}
                          onClick={() => setFindPastedUrl(h.url)}
                        >
                          <ListingThumb
                            urls={h.image_url ? [h.image_url] : null}
                            alt=""
                            sizeClass={wbFindThumbClass}
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-xs text-muted-foreground">{h.url}</span>
                            <span className="block">{h.label}</span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {findWbHits && findWbHits.length === 0 && !findWbSearchBusy ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  No watches found on WatchBase for that query.
                </p>
              ) : null}
              <div className="mt-4 space-y-2">
                <label className="text-sm font-medium" htmlFor="find-paste-url">
                  WatchBase page URL (confirm)
                </label>
                <Input
                  id="find-paste-url"
                  className="font-mono text-xs"
                  placeholder="https://watchbase.com/brand/family/ref-slug"
                  value={findPastedUrl}
                  onChange={(e) => setFindPastedUrl(e.target.value)}
                />
              </div>
              {selectedWbHit?.image_url ? (
                <div className="mt-4 rounded-md border border-border bg-muted/20 p-3">
                  <p className="mb-2 text-center text-xs font-medium text-muted-foreground">
                    Selected watch preview (same Photo size setting)
                  </p>
                  <div className="flex justify-center">
                    {/* eslint-disable-next-line @next/next/no-img-element -- WatchBase CDN */}
                    <img
                      src={selectedWbHit.image_url}
                      alt={selectedWbHit.label}
                      className={`${wbFindPreviewMaxClass} w-auto max-w-full rounded-md object-contain`}
                    />
                  </div>
                </div>
              ) : null}
              <div className="mt-6 flex flex-wrap justify-end gap-2">
                <Button type="button" variant="ghost" onClick={closeFindModal}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  disabled={importBusy || !findPastedUrl.trim()}
                  onClick={() => runWatchbaseImport(findPastedUrl, closeFindModal)}
                >
                  {importBusy ? "Importing…" : "Confirm import"}
                </Button>
              </div>
            </div>
          </div>
        </>
      ) : null}
      <div>
        <Button variant="ghost" className="mb-2 -ml-2" asChild>
          <Link href="/watch-models/">← Watch database</Link>
        </Button>
        <h1 className="text-2xl font-semibold">
          {isNew ? "New watch model" : "Edit watch model"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Reference + brand is the usual unique key; without reference, brand + model family. Listings
          auto-link when data matches; you can override on each listing.
        </p>
      </div>

      {!isNew && (referenceUrl.trim() || linkedEbayUrls.length > 0) ? (
        <Card>
          <CardHeader>
            <CardTitle>External links</CardTitle>
            <CardDescription>
              Open the WatchBase reference page or any eBay listing URL that is currently linked to this catalog
              row (active listings only).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {referenceUrl.trim() ? (
              <p>
                <span className="font-medium text-foreground">WatchBase: </span>
                <a
                  className="text-primary underline-offset-4 hover:underline break-all"
                  href={referenceUrl.trim()}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {referenceUrl.trim()}
                </a>
              </p>
            ) : null}
            {linkedEbayUrls.length > 0 ? (
              <div>
                <p className="font-medium text-foreground">eBay listings</p>
                <ul className="mt-1 list-inside list-disc space-y-1 text-muted-foreground">
                  {linkedEbayUrls.map((u) => (
                    <li key={u} className="break-all">
                      <a
                        className="text-primary underline-offset-4 hover:underline"
                        href={u}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {u}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Core identity</CardTitle>
          <CardDescription>Used for matching and display.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Brand *" id="brand" value={brand} onChange={setBrand} />
          <Field label="Reference" id="ref" value={reference} onChange={setReference} />
          <Field label="Model family" id="mf" value={modelFamily} onChange={setModelFamily} />
          <Field label="Model name" id="mn" value={modelName} onChange={setModelName} />
          <Field label="Caliber" id="cal" value={caliber} onChange={setCaliber} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>WatchBase &amp; external page</CardTitle>
          <CardDescription>
            Use <strong>Import from WatchBase</strong> or <strong>Refresh data from WatchBase</strong> to fetch
            this model’s public HTML and the same{" "}
            <code className="rounded bg-muted px-1">/prices</code> JSON the site uses for its chart (EUR list
            prices); min/max EUR are converted to GBP for <strong>Manual low / high</strong> (Frankfurter ECB
            rate, or <code className="rounded bg-muted px-1">EUR_GBP_RATE_FALLBACK</code> if the API fails).
            The <strong>Family</strong> row fills <strong>Model family</strong>. Only click when needed —
            keep volume low and comply with{" "}
            <a
              className="text-primary underline-offset-4 hover:underline"
              href="https://watchbase.com/terms"
              target="_blank"
              rel="noreferrer"
            >
              WatchBase terms
            </a>
            ; for automated or commercial scale use their{" "}
            <a
              className="text-primary underline-offset-4 hover:underline"
              href="https://watchbase.com/"
              target="_blank"
              rel="noreferrer"
            >
              Data Feed
            </a>
            . Paste the watch page in <strong>Reference URL</strong> (below) or rely on brand + family +
            reference; the import uses whatever is in that URL field — you do not need to save the form first.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!isNew ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="default"
                disabled={importBusy}
                onClick={() => runWatchbaseImport()}
              >
                {importBusy ? "Importing…" : "Import from WatchBase"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={importBusy}
                onClick={() => runWatchbaseImport()}
              >
                {importBusy ? "Refreshing…" : "Refresh data from WatchBase"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={importBusy}
                onClick={openFindWatchbaseWizard}
              >
                Find on WatchBase…
              </Button>
              {importDetail ? (
                <span className="text-xs text-muted-foreground">
                  Last: {importDetail.price_points} prices ·{" "}
                  <a
                    className="text-primary underline-offset-4 hover:underline"
                    href={importDetail.canonical_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    page
                  </a>
                </span>
              ) : null}
            </div>
          ) : null}
          {importMsg ? (
            <p
              className={`text-sm ${importMsg.includes("Imported") ? "text-muted-foreground" : "text-red-400"}`}
            >
              {importMsg}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            {wbGuess ? (
              <Button variant="outline" size="sm" asChild>
                <a href={wbGuess} target="_blank" rel="noopener noreferrer">
                  Open WatchBase (guess)
                </a>
              </Button>
            ) : (
              <Button type="button" variant="outline" size="sm" disabled title="Need brand, model family, and reference">
                Open WatchBase (guess)
              </Button>
            )}
            {wbGoogle ? (
              <Button variant="secondary" size="sm" asChild>
                <a href={wbGoogle} target="_blank" rel="noopener noreferrer">
                  Search WatchBase (Google)
                </a>
              </Button>
            ) : (
              <Button type="button" variant="secondary" size="sm" disabled title="Need reference">
                Search WatchBase (Google)
              </Button>
            )}
            {referenceUrl.trim() ? (
              <Button variant="ghost" size="sm" asChild>
                <a href={referenceUrl.trim()} target="_blank" rel="noopener noreferrer">
                  Open saved reference URL
                </a>
              </Button>
            ) : null}
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="refurl">
              Reference URL
            </label>
            <Input
              id="refurl"
              className="mt-1 font-mono text-xs"
              placeholder="https://watchbase.com/…"
              value={referenceUrl}
              onChange={(e) => setReferenceUrl(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Specifications (optional)</CardTitle>
          <CardDescription>
            Case, dial, and water resistance — useful when copied from a reference page such as WatchBase.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field
            label="Case materials"
            id="scm"
            value={specCaseMaterial}
            onChange={setSpecCaseMaterial}
          />
          <Field label="Bezel" id="sbz" value={specBezel} onChange={setSpecBezel} />
          <Field label="Crystal" id="scr" value={specCrystal} onChange={setSpecCrystal} />
          <Field label="Case back" id="scb" value={specCaseBack} onChange={setSpecCaseBack} />
          <Field
            label="Case diameter (mm)"
            id="scd"
            value={specCaseDia}
            onChange={setSpecCaseDia}
          />
          <Field
            label="Case height (mm)"
            id="sch"
            value={specCaseH}
            onChange={setSpecCaseH}
          />
          <Field label="Lug width (mm)" id="slw" value={specLug} onChange={setSpecLug} />
          <Field label="Water resistance (m)" id="swr" value={specWr} onChange={setSpecWr} />
          <Field
            label="Dial color"
            id="sdc"
            value={specDialColor}
            onChange={setSpecDialColor}
          />
          <Field
            label="Dial material"
            id="sdm"
            value={specDialMat}
            onChange={setSpecDialMat}
          />
          <Field
            label="Indexes / hands"
            id="sih"
            value={specIdxHands}
            onChange={setSpecIdxHands}
          />
        </CardContent>
      </Card>

      {extPrices?.points && extPrices.points.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>List prices (imported)</CardTitle>
            <CardDescription>
              Historical <strong>manufacturer / list</strong> prices from WatchBase’s chart (not live offers).
              Amounts are in{" "}
              <strong>{extPrices.currency === "EUR" ? "euros (€)" : extPrices.currency || "—"}</strong> · source{" "}
              {extPrices.source || "watchbase"}
              {extPrices.fetched_at ? ` · fetched ${extPrices.fetched_at.slice(0, 10)}` : ""}. Manual low/high on
              this page are converted to <strong>£ GBP</strong> when you import.
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full min-w-[320px] text-left text-sm">
              <thead className="border-b border-border text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">Date</th>
                  <th className="py-2 pr-3 font-medium">Series</th>
                  <th className="py-2 font-medium tabular-nums">Amount (import currency)</th>
                </tr>
              </thead>
              <tbody>
                {extPrices.points.map((p, i) => (
                  <tr key={`${p.date}-${i}`} className="border-b border-border/50">
                    <td className="py-1.5 pr-3">{p.date}</td>
                    <td className="py-1.5 pr-3">{p.series}</td>
                    <td className="py-1.5 tabular-nums">
                      {money(p.amount, extPrices.currency === "EUR" ? "EUR" : undefined)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Media &amp; notes</CardTitle>
          <CardDescription>
            When you add URLs, a preview and a clickable list appear above the text field. The large image uses the
            first line; <code className="rounded bg-muted px-1">/api/media/…</code> paths open via the API base.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {previewImageUrls.length > 0 ? (
            <div className="space-y-3 rounded-lg border border-border bg-muted/15 p-4">
              <p className="text-sm font-medium">Image preview</p>
              <div className="flex justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element -- dynamic catalog / eBay URLs */}
                <img
                  src={mediaUrl(previewImageUrls[0])}
                  alt={photoAlt}
                  className="max-h-[min(24rem,70vh)] w-auto max-w-full rounded-md border border-border bg-muted/30 object-contain shadow-sm"
                  referrerPolicy="no-referrer"
                />
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">URLs (same order as the field below)</p>
                <ul className="space-y-2 text-sm">
                  {previewImageUrls.map((u, i) => (
                    <li
                      key={`${i}-${u.slice(0, 48)}`}
                      className="rounded-md border border-border/80 bg-background/80 px-2 py-1.5"
                    >
                      <span className="mb-0.5 block text-xs text-muted-foreground">
                        {i === 0 ? "Line 1 (preview above)" : `Line ${i + 1}`}
                      </span>
                      <a
                        href={mediaUrl(u)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="break-all font-mono text-xs text-primary underline-offset-2 hover:underline"
                      >
                        {u}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}
          <div>
            <label className="text-sm font-medium" htmlFor="img">
              Image URLs (one per line)
            </label>
            <textarea
              id="img"
              rows={4}
              value={imageLines}
              onChange={(e) => setImageLines(e.target.value)}
              className="mt-1 flex w-full rounded-md border border-border bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            />
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="desc">
              Description
            </label>
            <textarea
              id="desc"
              rows={5}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 flex w-full rounded-md border border-border bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Production window</CardTitle>
          <CardDescription>
            Approximate years this reference was in production (from specs, import, or your own notes). Optional.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium" htmlFor="ps">
              Start
            </label>
            <Input
              id="ps"
              type="date"
              className="mt-1"
              value={prodStart}
              onChange={(e) => setProdStart(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="pe">
              End
            </label>
            <Input
              id="pe"
              type="date"
              className="mt-1"
              value={prodEnd}
              onChange={(e) => setProdEnd(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Price bounds</CardTitle>
          <CardDescription>
            All bounds on this card are stored and shown in <strong>British pounds (£)</strong>.{" "}
            <strong>Manual</strong> low/high are whatever you set (WatchBase import can pre-fill them from the
            EUR chart). <strong>Observed</strong> low/high are computed for you from asking prices on{" "}
            <strong>eBay listings linked</strong> to this model plus compatible <strong>recorded sale</strong>{" "}
            rows in your database — they refresh when you save this form or when a linked listing is
            re-analyzed.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium" htmlFor="ml">
              Manual low{currencyInputLabelSuffix("GBP")}
            </label>
            <Input
              id="ml"
              type="number"
              step="0.01"
              className="mt-1"
              value={manualLow}
              onChange={(e) => setManualLow(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="mh">
              Manual high{currencyInputLabelSuffix("GBP")}
            </label>
            <Input
              id="mh"
              type="number"
              step="0.01"
              className="mt-1"
              value={manualHigh}
              onChange={(e) => setManualHigh(e.target.value)}
            />
          </div>
          <div className="md:col-span-2 rounded-md border border-border bg-muted/20 p-3 text-sm">
            <p className="font-medium text-foreground">Observed (read-only)</p>
            <p className="mt-1 text-muted-foreground">
              The <strong>lowest and highest</strong> prices we see from data already in WatchFinder: current
              asking prices on <strong>linked eBay listings</strong> (that you have ingested) and any{" "}
              <strong>recorded sales</strong> you entered that match this catalog row. This is not a live
              market appraisal — it reflects your linked data only, in <strong>£</strong>.
            </p>
            <p className="mt-2 tabular-nums text-foreground">
              {money(observedLow, "GBP")} – {money(observedHigh, "GBP")}
            </p>
          </div>
        </CardContent>
      </Card>

      {saveErr ? <p className="text-sm text-red-400">{saveErr}</p> : null}
      <div className="flex flex-wrap gap-3">
        <Button type="button" disabled={saving} onClick={save}>
          {saving ? "Saving…" : "Save"}
        </Button>
        {!isNew ? (
          <Button
            type="button"
            variant="outline"
            className="border-red-800 text-red-400 hover:bg-red-950/40"
            disabled={deleting}
            onClick={remove}
          >
            {deleting ? "Deleting…" : "Delete"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function Field({
  label,
  id,
  value,
  onChange,
}: {
  label: string;
  id: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="text-sm font-medium" htmlFor={id}>
        {label}
      </label>
      <Input id={id} className="mt-1" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
