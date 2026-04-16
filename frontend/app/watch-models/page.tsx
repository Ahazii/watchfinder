"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { apiUrl, fetchJson } from "@/lib/api";
import { TABLE_THUMB_STORAGE, usePersistedTableThumbSize } from "@/lib/table-thumb-sizes";
import { TableThumbSizeSelect } from "@/components/table-thumb-size-select";
import { WatchbaseBatchWizard } from "@/components/watchbase-batch-wizard";
import type {
  BackfillEntityDictionariesResponse,
  BackfillWatchCatalogResponse,
  WatchModel,
  WatchModelListResponse,
} from "@/lib/types";
import { money } from "@/lib/format";
import {
  appendWatchModelListFilters,
  fetchAllWatchModels,
  sortIdsForBatch,
  type WatchModelListFilters,
} from "@/lib/watch-models-batch";
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

const WM_PAGE_SIZE_KEY = "watchfinder-watch-models-page-size";
const WM_PAGE_SIZE_OPTIONS = [25, 50, 100, 200, 500, "all"] as const;
type WatchModelsPageSize = (typeof WM_PAGE_SIZE_OPTIONS)[number];

function parseWatchModelsPageSize(raw: string | null): WatchModelsPageSize {
  if (raw === "all") return "all";
  const n = Number(raw);
  if (Number.isFinite(n) && [25, 50, 100, 200, 500].includes(n)) {
    return n as 25 | 50 | 100 | 200 | 500;
  }
  return 50;
}

export default function WatchModelsPage() {
  const [q, setQ] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const [referenceFilter, setReferenceFilter] = useState("");
  const [modelFamilyFilter, setModelFamilyFilter] = useState("");
  const [modelNameFilter, setModelNameFilter] = useState("");
  const [caliberFilter, setCaliberFilter] = useState("");
  const [pricingFilter, setPricingFilter] = useState<NonNullable<WatchModelListFilters["pricing"]>>("all");
  const [importStatusFilter, setImportStatusFilter] =
    useState<NonNullable<WatchModelListFilters["import_status"]>>("all");
  const [debouncedListFilters, setDebouncedListFilters] = useState<WatchModelListFilters>({});
  const [pageSize, setPageSizeState] = useState<WatchModelsPageSize>(() =>
    typeof window === "undefined" ? 50 : parseWatchModelsPageSize(localStorage.getItem(WM_PAGE_SIZE_KEY)),
  );
  const [skip, setSkip] = useState(0);
  const [rows, setRows] = useState<WatchModel[]>([]);
  const [total, setTotal] = useState(0);
  const [loadBusy, setLoadBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [backfillBusy, setBackfillBusy] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);
  const [entityBackfillBusy, setEntityBackfillBusy] = useState(false);
  const [entityBackfillMsg, setEntityBackfillMsg] = useState<string | null>(null);
  const { sizeId: thumbSizeId, setSizeId: setThumbSizeId, sizeClass: thumbSizeClass } =
    usePersistedTableThumbSize(TABLE_THUMB_STORAGE.watchDatabase);

  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const shiftAnchorRef = useRef<number | null>(null);
  const [presetBusy, setPresetBusy] = useState(false);
  const [presetErr, setPresetErr] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardOrderedIds, setWizardOrderedIds] = useState<string[]>([]);
  const [bulkDeleteBusy, setBulkDeleteBusy] = useState(false);

  const rowOrderHint = useMemo(() => new Map(rows.map((r, i) => [r.id, i])), [rows]);

  const setPageSize = useCallback((v: WatchModelsPageSize) => {
    setPageSizeState(v);
    try {
      localStorage.setItem(WM_PAGE_SIZE_KEY, String(v));
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      const next: WatchModelListFilters = {};
      const qt = q.trim();
      const bt = brandFilter.trim();
      const rt = referenceFilter.trim();
      const ft = modelFamilyFilter.trim();
      const nt = modelNameFilter.trim();
      const ct = caliberFilter.trim();
      if (qt) next.q = qt;
      if (bt) next.brand = bt;
      if (rt) next.reference = rt;
      if (ft) next.model_family = ft;
      if (nt) next.model_name = nt;
      if (ct) next.caliber = ct;
      if (pricingFilter !== "all") next.pricing = pricingFilter;
      if (importStatusFilter !== "all") next.import_status = importStatusFilter;
      setDebouncedListFilters((prev) => {
        const same =
          (prev.q ?? "") === (next.q ?? "") &&
          (prev.brand ?? "") === (next.brand ?? "") &&
          (prev.reference ?? "") === (next.reference ?? "") &&
          (prev.model_family ?? "") === (next.model_family ?? "") &&
          (prev.model_name ?? "") === (next.model_name ?? "") &&
          (prev.caliber ?? "") === (next.caliber ?? "") &&
          (prev.pricing ?? "all") === (next.pricing ?? "all") &&
          (prev.import_status ?? "all") === (next.import_status ?? "all");
        return same ? prev : next;
      });
    }, 300);
    return () => clearTimeout(t);
  }, [
    q,
    brandFilter,
    referenceFilter,
    modelFamilyFilter,
    modelNameFilter,
    caliberFilter,
    pricingFilter,
    importStatusFilter,
  ]);

  useEffect(() => {
    setSkip(0);
  }, [debouncedListFilters]);

  useEffect(() => {
    setSkip(0);
  }, [pageSize]);

  const load = useCallback(() => {
    setErr(null);
    setLoadBusy(true);
    if (pageSize === "all") {
      fetchAllWatchModels(debouncedListFilters)
        .then((items) => {
          setRows(items);
          setTotal(items.length);
        })
        .catch((e: Error) => setErr(e.message))
        .finally(() => setLoadBusy(false));
      return;
    }
    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(pageSize),
    });
    appendWatchModelListFilters(params, debouncedListFilters);
    fetchJson<WatchModelListResponse>(`/api/watch-models?${params}`)
      .then((r) => {
        setRows(r.items);
        setTotal(r.total);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoadBusy(false));
  }, [skip, debouncedListFilters, pageSize]);

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
          `Scanned ${r.scanned}: ${r.created_new} new catalog rows, ${r.linked_existing} linked to existing rows, ${r.already_linked} already linked, ${r.queued_for_review ?? 0} queued for review, ${r.skipped_no_identity} skipped (missing brand and reference/family), ${r.skipped_excluded_brand ?? 0} skipped (excluded brand — see WATCH_CATALOG_EXCLUDED_BRANDS).`,
        );
        load();
      })
      .catch((e: Error) => setBackfillMsg(e.message))
      .finally(() => setBackfillBusy(false));
  };

  const runEntityBackfill = () => {
    setEntityBackfillBusy(true);
    setEntityBackfillMsg(null);
    fetch(apiUrl("/api/watch-models/backfill-entity-dictionaries"), {
      method: "POST",
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<BackfillEntityDictionariesResponse>;
      })
      .then((r) => {
        setEntityBackfillMsg(
          `Scanned ${r.scanned}: ${r.with_resolved_brand} with resolved brand, ${r.with_resolved_reference} with stock reference, ${r.with_caliber_link} with caliber link; inferred ${r.inferred_brand ?? 0} brand (cal+ref), ${r.inferred_caliber ?? 0} caliber (brand+ref), ${r.inferred_reference ?? 0} reference (brand+cal).`,
        );
      })
      .catch((e: Error) => setEntityBackfillMsg(e.message))
      .finally(() => setEntityBackfillBusy(false));
  };

  const handleCheckboxChange = (id: string, rowIndex: number, checked: boolean, shiftKey: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (shiftKey && shiftAnchorRef.current !== null) {
        const lo = Math.min(shiftAnchorRef.current, rowIndex);
        const hi = Math.max(shiftAnchorRef.current, rowIndex);
        for (let i = lo; i <= hi; i++) {
          const rid = rows[i]?.id;
          if (!rid) continue;
          if (checked) next.add(rid);
          else next.delete(rid);
        }
      } else {
        shiftAnchorRef.current = rowIndex;
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  };

  const selectAllOnPage = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const r of rows) next.add(r.id);
      return next;
    });
    shiftAnchorRef.current = rows.length ? 0 : null;
  };

  const selectNone = () => {
    setSelected(new Set());
    shiftAnchorRef.current = null;
  };

  const runPreset = async (extraFilters: Partial<WatchModelListFilters>) => {
    setPresetErr(null);
    setPresetBusy(true);
    try {
      const all = await fetchAllWatchModels({ ...debouncedListFilters, ...extraFilters });
      const ids = new Set(all.map((m) => m.id));
      setSelected(ids);
      shiftAnchorRef.current = null;
    } catch (e) {
      setPresetErr((e as Error).message);
    } finally {
      setPresetBusy(false);
    }
  };

  const startWizard = () => {
    if (selected.size === 0) return;
    const ordered = sortIdsForBatch(selected, rowOrderHint);
    setWizardOrderedIds(ordered);
    setWizardOpen(true);
  };

  const deleteSelected = async () => {
    if (selected.size === 0) return;
    const ids = Array.from(selected);
    const n = ids.length;
    if (
      !window.confirm(
        `Delete ${n} catalog row${n === 1 ? "" : "s"}? Linked listings will be unlinked (FK SET NULL). This cannot be undone.`,
      )
    ) {
      return;
    }
    setBulkDeleteBusy(true);
    setErr(null);
    let ok = 0;
    let lastErr = "";
    for (const id of ids) {
      try {
        const res = await fetch(apiUrl(`/api/watch-models/${id}`), { method: "DELETE" });
        if (!res.ok) lastErr = await res.text();
        else ok += 1;
      } catch (e) {
        lastErr = (e as Error).message;
      }
    }
    setBulkDeleteBusy(false);
    setSelected(new Set());
    shiftAnchorRef.current = null;
    if (ok < n) {
      setErr(
        lastErr
          ? `Deleted ${ok} of ${n}. Last error: ${lastErr}`
          : `Deleted ${ok} of ${n}.`,
      );
    }
    load();
  };

  const onWizardDeleted = useCallback(
    (id: string) => {
      setWizardOrderedIds((prev) => prev.filter((x) => x !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      load();
    },
    [load],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Watch database</h1>
          <p className="mt-1 text-muted-foreground">
            Canonical models (brand + reference or family). Many listings can link to one row.{" "}
            <strong>Observed</strong> and <strong>manual</strong> columns are price ranges in{" "}
            <strong>British pounds (£)</strong> — observed values come from linked eBay listings and recorded
            sales in your database.
          </p>
        </div>
        <Button asChild>
          <Link href="/watch-models/detail/">Add model</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Supervised WatchBase import (batch)</CardTitle>
          <CardDescription>
            Select rows with checkboxes (Shift+click to range-select on the <strong>current page</strong>).
            Presets load the <strong>whole catalog</strong> matching your search and field filters (same as the
            table),
            then replace the selection. Each watch runs a WatchBase search, shows large images side by side, and
            requires <strong>Yes</strong> on a match or <strong>No match</strong> to skip. Random 1–5 s delay
            between WatchBase requests. Open <strong>full detail</strong> in a new tab from the wizard when you
            need more context. Comply with{" "}
            <a
              className="text-primary underline-offset-4 hover:underline"
              href="https://watchbase.com/terms"
              target="_blank"
              rel="noreferrer"
            >
              WatchBase terms
            </a>
            .
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">{selected.size} selected</span>
          <Button type="button" variant="outline" size="sm" onClick={selectAllOnPage} disabled={rows.length === 0}>
            Select all on page
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={selectNone} disabled={selected.size === 0}>
            Select none
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={presetBusy}
            onClick={() => runPreset({ import_status: "unmatched" })}
          >
            {presetBusy ? "Loading…" : "Select unmatched (catalog)"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={presetBusy}
            onClick={() => runPreset({ pricing: "strict_needs" })}
          >
            {presetBusy ? "Loading…" : "Select without pricing (catalog)"}
          </Button>
          <Button type="button" disabled={selected.size === 0} onClick={startWizard}>
            Start supervised import…
          </Button>
          <Button
            type="button"
            variant="outline"
            className="border-red-800 text-red-400 hover:bg-red-950/40"
            disabled={selected.size === 0 || bulkDeleteBusy}
            onClick={() => void deleteSelected()}
          >
            {bulkDeleteBusy ? "Deleting…" : `Delete selected (${selected.size})`}
          </Button>
        </CardContent>
        {presetErr ? <p className="mt-2 text-sm text-red-400">{presetErr}</p> : null}
        <CardContent className="border-t border-border pt-4 text-xs text-muted-foreground">
          <strong>Unmatched:</strong> no Reference URL <em>or</em> never WatchBase-imported (same as{" "}
          <strong>WatchBase</strong> filter below). <strong>Without pricing:</strong> no WatchBase price points{" "}
          <em>or</em> both manual £ low/high empty (strict rule). Presets merge with your search/field filters.
        </CardContent>
      </Card>

      <WatchbaseBatchWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        orderedIds={wizardOrderedIds}
        onImported={load}
        onDeleted={onWizardDeleted}
      />

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
          <CardTitle>Backfill entity dictionaries</CardTitle>
          <CardDescription>
            Scan every <strong>active</strong> listing and resolve <strong>brand</strong>,{" "}
            <strong>caliber</strong>, and <strong>stock reference</strong> rows (fuzzy match + infer brand
            from caliber+reference when possible). Separate from watch catalog linking above. Safe to run
            repeatedly.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Button type="button" disabled={entityBackfillBusy} onClick={runEntityBackfill}>
            {entityBackfillBusy ? "Running…" : "Run entity dictionary backfill"}
          </Button>
          {entityBackfillMsg ? (
            <p className="text-sm text-muted-foreground">{entityBackfillMsg}</p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Search and filters</CardTitle>
          <CardDescription>
            <strong>Search</strong> matches brand, reference, family, or model name (OR). Field boxes narrow
            further (contains, AND with each other and with search). Excluded brands are set in{" "}
            <Link href="/settings/" className="text-primary underline-offset-4 hover:underline">
              Settings
            </Link>{" "}
            and/or <code className="rounded bg-muted px-1">WATCH_CATALOG_EXCLUDED_BRANDS</code> (both merged); those
            rows never appear here or in listing link pickers, and backfill skips linking/creating them.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="wm-search-q">
              Search (any of brand / reference / family / model name)
            </label>
            <Input
              id="wm-search-q"
              placeholder="Search…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="wm-filter-brand">
              Brand
            </label>
            <Input
              id="wm-filter-brand"
              placeholder="Contains…"
              value={brandFilter}
              onChange={(e) => setBrandFilter(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="wm-filter-ref">
              Reference
            </label>
            <Input
              id="wm-filter-ref"
              placeholder="Contains…"
              value={referenceFilter}
              onChange={(e) => setReferenceFilter(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="wm-filter-family">
              Model family
            </label>
            <Input
              id="wm-filter-family"
              placeholder="Contains…"
              value={modelFamilyFilter}
              onChange={(e) => setModelFamilyFilter(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="wm-filter-name">
              Model name
            </label>
            <Input
              id="wm-filter-name"
              placeholder="Contains…"
              value={modelNameFilter}
              onChange={(e) => setModelNameFilter(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="wm-filter-caliber">
              Caliber
            </label>
            <Input
              id="wm-filter-caliber"
              placeholder="Contains…"
              value={caliberFilter}
              onChange={(e) => setCaliberFilter(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="wm-filter-pricing">
              Price data
            </label>
            <select
              id="wm-filter-pricing"
              className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={pricingFilter}
              onChange={(e) =>
                setPricingFilter(e.target.value as NonNullable<WatchModelListFilters["pricing"]>)
              }
            >
              <option value="all">All</option>
              <option value="has_signal">Has signal (manual, observed, or WatchBase points)</option>
              <option value="missing_signal">Missing all of the above</option>
              <option value="strict_needs">Strict: needs work (no points or no manual £)</option>
              <option value="strict_ok">Strict: has points and manual £</option>
            </select>
          </div>
          <div>
            <label
              className="mb-1 block text-xs font-medium text-muted-foreground"
              htmlFor="wm-filter-import"
            >
              WatchBase
            </label>
            <select
              id="wm-filter-import"
              className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={importStatusFilter}
              onChange={(e) =>
                setImportStatusFilter(e.target.value as NonNullable<WatchModelListFilters["import_status"]>)
              }
            >
              <option value="all">All</option>
              <option value="unmatched">Unmatched (no ref URL or never imported)</option>
              <option value="matched">Matched (URL + imported)</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {err ? <p className="text-sm text-red-400">{err}</p> : null}

      <div className="flex flex-wrap items-center justify-end gap-3 text-sm text-muted-foreground">
        {loadBusy ? (
          <span className="text-muted-foreground" aria-live="polite">
            Loading…
          </span>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="wm-page-size" className="text-xs font-medium text-muted-foreground">
            Rows per page
          </label>
          <select
            id="wm-page-size"
            className="h-9 rounded-md border border-input bg-background px-2 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            value={String(pageSize)}
            onChange={(e) => {
              const v = e.target.value;
              setPageSize(v === "all" ? "all" : parseWatchModelsPageSize(v));
            }}
          >
            {WM_PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={String(opt)} value={String(opt)}>
                {opt === "all" ? "All (matching filters)" : opt}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="border-b border-border bg-muted/40">
            <tr>
              <th className="w-10 px-2 py-2 font-medium" title="Shift+click for range on this page">
                <span className="sr-only">Select</span>
              </th>
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
              <th className="px-3 py-2 font-medium align-top">
                <span className="block">Observed</span>
                <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
                  Auto £ range from linked data
                </span>
              </th>
              <th className="px-3 py-2 font-medium align-top">
                <span className="block">Manual</span>
                <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
                  Your £ bounds
                </span>
              </th>
              <th className="px-3 py-2 font-medium w-36">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-muted-foreground">
                  No models yet. Add one or widen your search.
                </td>
              </tr>
            ) : (
              rows.map((m, rowIndex) => (
                <tr key={m.id} className="border-b border-border/60">
                  <td className="px-2 py-2 align-top">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-border"
                      checked={selected.has(m.id)}
                      onChange={(e) =>
                        handleCheckboxChange(
                          m.id,
                          rowIndex,
                          e.target.checked,
                          (e.nativeEvent as globalThis.MouseEvent).shiftKey,
                        )
                      }
                      aria-label={`Select ${label(m)}`}
                    />
                  </td>
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
                    {money(m.observed_price_low, "GBP")} – {money(m.observed_price_high, "GBP")}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">
                    {money(m.manual_price_low, "GBP")} – {money(m.manual_price_high, "GBP")}
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
          {pageSize === "all"
            ? total === 0
              ? "0"
              : `All ${total} shown`
            : total === 0
              ? "0"
              : `${skip + 1}–${Math.min(skip + rows.length, total)} of ${total}`}
        </span>
        {pageSize !== "all" ? (
          <>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={skip <= 0 || loadBusy}
              onClick={() => setSkip((s) => Math.max(0, s - pageSize))}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={skip + pageSize >= total || loadBusy}
              onClick={() => setSkip((s) => s + pageSize)}
            >
              Next
            </Button>
          </>
        ) : null}
      </div>
    </div>
  );
}
