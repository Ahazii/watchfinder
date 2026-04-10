"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiUrl, fetchJson, mediaUrl } from "@/lib/api";
import type {
  UnifiedMarketHit,
  UnifiedMarketSearchResponse,
  WatchBaseImportResult,
  WatchModel,
} from "@/lib/types";
import {
  buildWatchbaseSearchQuery,
  randomWatchbaseDelayMs,
  sleep,
} from "@/lib/watch-models-batch";
import { watchbaseGoogleSiteSearchUrl } from "@/lib/watchbase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MarketMatchRow } from "@/components/market-match-row";

type Props = {
  open: boolean;
  onClose: () => void;
  orderedIds: string[];
  onImported: () => void;
  /** After DELETE; parent should remove id from queue and selection. */
  onDeleted?: (id: string) => void;
};

export function WatchbaseBatchWizard({
  open,
  onClose,
  orderedIds,
  onImported,
  onDeleted,
}: Props) {
  const [stepIndex, setStepIndex] = useState(0);
  const [modalPos, setModalPos] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  } | null>(null);

  const [phaseBusy, setPhaseBusy] = useState(false);
  const [currentModel, setCurrentModel] = useState<WatchModel | null>(null);
  const [hits, setHits] = useState<UnifiedMarketHit[] | null>(null);
  const [autoUnified, setAutoUnified] = useState<UnifiedMarketSearchResponse | null>(null);
  const [searchErr, setSearchErr] = useState<string | null>(null);
  const [importErr, setImportErr] = useState<string | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [lastOk, setLastOk] = useState<WatchBaseImportResult | null>(null);

  const [manualQuery, setManualQuery] = useState("");
  const [manualHits, setManualHits] = useState<UnifiedMarketHit[] | null>(null);
  const [manualUnified, setManualUnified] = useState<UnifiedMarketSearchResponse | null>(null);
  const [manualBusy, setManualBusy] = useState(false);
  const [manualErr, setManualErr] = useState<string | null>(null);
  const [pastedUrl, setPastedUrl] = useState("");

  const total = orderedIds.length;
  const done = total === 0 || stepIndex >= total;
  const currentId = !done ? orderedIds[stepIndex] : null;

  useEffect(() => {
    if (!open) {
      setStepIndex(0);
      setCurrentModel(null);
      setHits(null);
      setSearchErr(null);
      setImportErr(null);
      setLastOk(null);
      setManualHits(null);
      setManualErr(null);
      setManualQuery("");
      setPastedUrl("");
      setAutoUnified(null);
      setManualUnified(null);
      return;
    }
    if (typeof window !== "undefined") {
      const panelW = Math.min(900, window.innerWidth - 32);
      setModalPos({
        x: Math.max(8, Math.round((window.innerWidth - panelW) / 2)),
        y: Math.max(8, Math.round(window.innerHeight * 0.04)),
      });
    }
  }, [open]);

  useEffect(() => {
    if (!open || done || !currentId) return;
    let cancelled = false;

    const run = async () => {
      setPhaseBusy(true);
      setCurrentModel(null);
      setHits(null);
      setSearchErr(null);
      setImportErr(null);
      setLastOk(null);
      setManualHits(null);
      setManualErr(null);
      setPastedUrl("");
      setAutoUnified(null);
      setManualUnified(null);
      try {
        await sleep(randomWatchbaseDelayMs());
        if (cancelled) return;
        const m = await fetchJson<WatchModel>(`/api/watch-models/${currentId}`);
        if (cancelled) return;
        setCurrentModel(m);
        setManualQuery(buildWatchbaseSearchQuery(m));

        const q = buildWatchbaseSearchQuery(m);
        if (!q) {
          setHits([]);
          setAutoUnified(null);
          setSearchErr(null);
          setPhaseBusy(false);
          return;
        }
        await sleep(randomWatchbaseDelayMs());
        if (cancelled) return;
        const p = new URLSearchParams();
        p.set("q", q);
        p.set("brand", m.brand);
        if (m.reference?.trim()) p.set("reference", m.reference.trim());
        if (m.model_family?.trim()) p.set("model_family", m.model_family.trim());
        const u = await fetchJson<UnifiedMarketSearchResponse>(`/api/market/search?${p.toString()}`);
        if (!cancelled) {
          setHits(u.watchbase.items);
          setAutoUnified(u);
        }
      } catch (e) {
        if (!cancelled) {
          setSearchErr((e as Error).message);
          setHits([]);
        }
      } finally {
        if (!cancelled) setPhaseBusy(false);
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [open, done, currentId]);

  const onDragMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      origX: modalPos.x,
      origY: modalPos.y,
    };
  };

  useEffect(() => {
    if (!open) return;
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
  }, [open, modalPos.x, modalPos.y]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const runImport = useCallback(
    async (referenceUrl: string) => {
      if (!currentModel) return;
      setImportBusy(true);
      setImportErr(null);
      setLastOk(null);
      try {
        await sleep(randomWatchbaseDelayMs());
        const res = await fetch(apiUrl(`/api/watch-models/${currentModel.id}/import-watchbase`), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ reference_url: referenceUrl.trim() }),
        });
        const text = await res.text();
        if (!res.ok) {
          let msg = text;
          try {
            const j = JSON.parse(text) as { detail?: string };
            if (typeof j.detail === "string") msg = j.detail;
          } catch {
            /* keep text */
          }
          throw new Error(msg);
        }
        const r = JSON.parse(text) as WatchBaseImportResult;
        setLastOk(r);
        onImported();
        setStepIndex((i) => i + 1);
      } catch (e) {
        setImportErr((e as Error).message);
      } finally {
        setImportBusy(false);
      }
    },
    [currentModel, onImported],
  );

  const skipNoMatch = useCallback(() => {
    setImportErr(null);
    setLastOk(null);
    setStepIndex((i) => i + 1);
  }, []);

  const runManualSearch = useCallback(async () => {
    const q = manualQuery.trim();
    if (!q) return;
    setManualBusy(true);
    setManualErr(null);
    setManualHits(null);
    setManualUnified(null);
    try {
      await sleep(randomWatchbaseDelayMs());
      const p = new URLSearchParams();
      p.set("q", q);
      if (currentModel) {
        p.set("brand", currentModel.brand);
        if (currentModel.reference?.trim()) p.set("reference", currentModel.reference.trim());
        if (currentModel.model_family?.trim()) p.set("model_family", currentModel.model_family.trim());
      }
      const u = await fetchJson<UnifiedMarketSearchResponse>(`/api/market/search?${p.toString()}`);
      setManualHits(u.watchbase.items);
      setManualUnified(u);
    } catch (e) {
      setManualErr((e as Error).message);
      setManualHits([]);
    } finally {
      setManualBusy(false);
    }
  }, [manualQuery, currentModel]);

  const deleteCurrent = useCallback(async () => {
    if (!currentModel || !onDeleted) return;
    if (
      !window.confirm(
        `Delete this catalog row?\n\n${currentModel.brand} ${currentModel.reference ?? ""}\n\nLinked listings will be unlinked (FK SET NULL). This cannot be undone.`,
      )
    ) {
      return;
    }
    setDeleteBusy(true);
    setImportErr(null);
    try {
      const res = await fetch(apiUrl(`/api/watch-models/${currentModel.id}`), { method: "DELETE" });
      if (!res.ok) throw new Error(await res.text());
      onDeleted(currentModel.id);
    } catch (e) {
      setImportErr((e as Error).message);
    } finally {
      setDeleteBusy(false);
    }
  }, [currentModel, onDeleted]);

  if (!open) return null;

  const ourImage = currentModel?.image_urls?.find((u) => typeof u === "string" && u.trim())?.trim();
  const googleUrl = watchbaseGoogleSiteSearchUrl(
    manualQuery.trim() || (currentModel ? buildWatchbaseSearchQuery(currentModel) : "") || "",
  );

  return (
    <>
      <div className="pointer-events-none fixed inset-0 z-40 bg-black/40" aria-hidden />
      <div
        role="dialog"
        aria-modal="false"
        aria-labelledby="wb-batch-title"
        className="fixed z-50 w-[calc(100%-1rem)] max-w-5xl overflow-hidden rounded-lg border border-border bg-background text-foreground shadow-xl"
        style={{ left: modalPos.x, top: modalPos.y }}
      >
        <div
          className="flex cursor-grab select-none items-start gap-2 border-b border-border bg-muted/40 px-4 py-3 active:cursor-grabbing"
          onMouseDown={onDragMouseDown}
        >
          <div className="min-w-0 flex-1">
            <h2 id="wb-batch-title" className="text-lg font-semibold leading-tight">
              Supervised WatchBase import
            </h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Drag header to move. Use <strong>Manual search</strong> if auto results are wrong. Random 1–5 s
              delay between WatchBase calls. Escape closes (progress is not saved).
            </p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        <div className="max-h-[min(85vh,900px)] overflow-y-auto p-4">
          {total === 0 ? (
            <p className="text-sm text-muted-foreground">No watches in the queue.</p>
          ) : done ? (
            <p className="text-sm text-muted-foreground">
              Finished all <strong>{total}</strong> selected model(s). Close to return to the list.
            </p>
          ) : (
            <>
              <p className="text-sm font-medium text-foreground">
                Step {stepIndex + 1} of {total}
                {currentModel ? (
                  <>
                    {" "}
                    ·{" "}
                    <Link
                      href={`/watch-models/detail/?id=${currentModel.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline-offset-2 hover:underline"
                    >
                      Open full detail (new tab)
                    </Link>
                  </>
                ) : null}
              </p>

              {phaseBusy ? (
                <p className="mt-4 text-sm text-muted-foreground">Loading model and WatchBase search…</p>
              ) : currentModel ? (
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-lg border border-border bg-muted/15 p-4">
                    <p className="text-sm font-semibold text-foreground">Your database</p>
                    <div className="mt-3 flex justify-center">
                      {ourImage ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={mediaUrl(ourImage)}
                          alt=""
                          className="max-h-72 max-w-full rounded-md border border-border object-contain bg-muted/30"
                          referrerPolicy="no-referrer"
                        />
                      ) : (
                        <div className="flex h-48 w-full max-w-xs items-center justify-center rounded-md border border-dashed border-border text-sm text-muted-foreground">
                          No image
                        </div>
                      )}
                    </div>
                    <dl className="mt-3 space-y-1 text-sm">
                      <div>
                        <dt className="text-muted-foreground">Brand</dt>
                        <dd className="font-medium">{currentModel.brand}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Reference</dt>
                        <dd>{currentModel.reference ?? "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Model family</dt>
                        <dd>{currentModel.model_family ?? "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Model name</dt>
                        <dd>{currentModel.model_name ?? "—"}</dd>
                      </div>
                      {currentModel.reference_url?.trim() ? (
                        <div>
                          <dt className="text-muted-foreground">Saved Reference URL</dt>
                          <dd className="break-all font-mono text-xs">{currentModel.reference_url.trim()}</dd>
                        </div>
                      ) : null}
                    </dl>
                    {onDeleted ? (
                      <div className="mt-4 border-t border-border pt-4">
                        <Button
                          type="button"
                          variant="outline"
                          className="w-full border-red-800 text-red-400 hover:bg-red-950/40"
                          disabled={deleteBusy || importBusy}
                          onClick={() => void deleteCurrent()}
                        >
                          {deleteBusy ? "Deleting…" : "Delete this catalog entry"}
                        </Button>
                      </div>
                    ) : null}
                  </div>

                  <div className="space-y-4">
                    <div className="rounded-lg border border-border p-4">
                      <p className="text-sm font-semibold text-foreground">WatchBase — auto search</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Query:{" "}
                        <span className="font-mono">{buildWatchbaseSearchQuery(currentModel) || "—"}</span>
                      </p>
                      {searchErr ? (
                        <p className="mt-2 text-sm text-red-400">{searchErr}</p>
                      ) : null}

                      <div className="mt-3 space-y-3">
                        {currentModel.reference_url?.trim() ? (
                          <div className="rounded-md border border-primary/40 bg-primary/5 p-3">
                            <p className="text-xs font-medium text-muted-foreground">Saved URL option</p>
                            <Button
                              type="button"
                              className="mt-2 w-full"
                              disabled={importBusy}
                              onClick={() => runImport(currentModel.reference_url!.trim())}
                            >
                              {importBusy ? "Importing…" : "Yes — import using saved Reference URL"}
                            </Button>
                          </div>
                        ) : null}

                        {hits && hits.length === 0 && !searchErr ? (
                          <p className="text-sm text-muted-foreground">No WatchBase search results.</p>
                        ) : null}

                        {autoUnified && (autoUnified.everywatch?.items?.length ?? 0) > 0 ? (
                          <div className="rounded-md border border-amber-900/30 bg-amber-950/10 p-3 text-xs">
                            <p className="font-medium text-foreground">Everywatch</p>
                            <ul className="mt-2 max-h-[min(36vh,14rem)] space-y-2 overflow-y-auto">
                              {autoUnified.everywatch.items.slice(0, 12).map((h) => (
                                <li key={h.url}>
                                  <MarketMatchRow
                                    href={h.url}
                                    title={h.label}
                                    imageUrl={h.image_url}
                                    priceHint={h.price_hint}
                                  />
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {autoUnified?.chrono24 ? (
                          <div className="rounded-md border border-border bg-muted/10 p-3 text-xs">
                            <p className="font-medium">Chrono24</p>
                            {autoUnified.chrono24.error ? (
                              <p className="mt-1 text-amber-200/80">{autoUnified.chrono24.error}</p>
                            ) : null}
                            <div className="mt-2 flex flex-wrap gap-2">
                              {autoUnified.chrono24.search_url ? (
                                <Button variant="outline" size="sm" asChild>
                                  <a href={autoUnified.chrono24.search_url} target="_blank" rel="noopener noreferrer">
                                    Open Chrono24
                                  </a>
                                </Button>
                              ) : null}
                              {autoUnified.chrono24.google_site_url ? (
                                <Button variant="outline" size="sm" asChild>
                                  <a
                                    href={autoUnified.chrono24.google_site_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    Google Chrono24
                                  </a>
                                </Button>
                              ) : null}
                            </div>
                          </div>
                        ) : null}
                        {hits?.map((h) => (
                          <div
                            key={h.url}
                            className="flex flex-col gap-2 rounded-md border border-border bg-muted/10 p-3 sm:flex-row"
                          >
                            <div className="flex shrink-0 justify-center sm:w-40">
                              {h.image_url ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img
                                  src={h.image_url}
                                  alt=""
                                  className="max-h-56 max-w-full rounded border border-border object-contain bg-muted/40"
                                  referrerPolicy="no-referrer"
                                />
                              ) : (
                                <div className="flex h-40 w-32 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
                                  No image
                                </div>
                              )}
                            </div>
                            <div className="min-w-0 flex-1 space-y-2">
                              <p className="text-sm font-medium leading-snug">{h.label}</p>
                              <p className="break-all font-mono text-xs text-muted-foreground">{h.url}</p>
                              <Button
                                type="button"
                                size="sm"
                                disabled={importBusy}
                                onClick={() => runImport(h.url)}
                              >
                                {importBusy ? "Importing…" : "Yes — import this WatchBase page"}
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-lg border border-amber-900/40 bg-amber-950/15 p-4">
                      <p className="text-sm font-semibold text-foreground">Fix match — manual market search</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        WatchBase rows can be imported; Everywatch/Chrono24 are for context (same API as detail page).
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Input
                          className="min-w-[200px] flex-1 font-mono text-xs"
                          value={manualQuery}
                          onChange={(e) => setManualQuery(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              void runManualSearch();
                            }
                          }}
                          placeholder="e.g. Cartier W7100046"
                        />
                        <Button type="button" disabled={manualBusy || importBusy} onClick={() => void runManualSearch()}>
                          {manualBusy ? "Searching…" : "Search markets"}
                        </Button>
                        {googleUrl ? (
                          <Button variant="outline" size="sm" asChild>
                            <a href={googleUrl} target="_blank" rel="noopener noreferrer">
                              Open Google (site:watchbase.com)
                            </a>
                          </Button>
                        ) : null}
                      </div>
                      {manualErr ? <p className="mt-2 text-sm text-red-400">{manualErr}</p> : null}
                      <div className="mt-3 space-y-3">
                        {manualHits?.map((h) => (
                          <div
                            key={`m-${h.url}`}
                            className="flex flex-col gap-2 rounded-md border border-border bg-muted/10 p-3 sm:flex-row"
                          >
                            <div className="flex shrink-0 justify-center sm:w-36">
                              {h.image_url ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img
                                  src={h.image_url}
                                  alt=""
                                  className="max-h-48 max-w-full rounded border border-border object-contain bg-muted/40"
                                  referrerPolicy="no-referrer"
                                />
                              ) : (
                                <div className="flex h-36 w-28 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
                                  No image
                                </div>
                              )}
                            </div>
                            <div className="min-w-0 flex-1 space-y-2">
                              <p className="text-sm font-medium leading-snug">{h.label}</p>
                              <p className="break-all font-mono text-xs text-muted-foreground">{h.url}</p>
                              <Button
                                type="button"
                                size="sm"
                                disabled={importBusy}
                                onClick={() => runImport(h.url)}
                              >
                                {importBusy ? "Importing…" : "Import this result"}
                              </Button>
                            </div>
                          </div>
                        ))}
                        {manualUnified && (manualUnified.everywatch?.items?.length ?? 0) > 0 ? (
                          <div className="rounded-md border border-amber-900/30 bg-amber-950/10 p-3 text-xs">
                            <p className="font-medium">Everywatch</p>
                            <ul className="mt-1 max-h-28 space-y-1 overflow-y-auto">
                              {manualUnified.everywatch.items.slice(0, 10).map((h) => (
                                <li key={h.url}>
                                  <a
                                    href={h.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary underline-offset-2 hover:underline break-all"
                                  >
                                    {h.price_hint ? `${h.price_hint} · ` : ""}
                                    {h.label.slice(0, 72)}
                                  </a>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {manualUnified?.chrono24 ? (
                          <div className="rounded-md border border-border bg-muted/10 p-3 text-xs">
                            <p className="font-medium">Chrono24</p>
                            {manualUnified.chrono24.error ? (
                              <p className="mt-1 text-amber-200/80">{manualUnified.chrono24.error}</p>
                            ) : null}
                            <div className="mt-2 flex flex-wrap gap-2">
                              {manualUnified.chrono24.search_url ? (
                                <Button variant="outline" size="sm" asChild>
                                  <a href={manualUnified.chrono24.search_url} target="_blank" rel="noopener noreferrer">
                                    Open Chrono24
                                  </a>
                                </Button>
                              ) : null}
                              {manualUnified.chrono24.google_site_url ? (
                                <Button variant="outline" size="sm" asChild>
                                  <a
                                    href={manualUnified.chrono24.google_site_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    Google Chrono24
                                  </a>
                                </Button>
                              ) : null}
                            </div>
                          </div>
                        ) : null}
                      </div>
                      <div className="mt-4 space-y-2 border-t border-border pt-4">
                        <label className="text-xs font-medium text-muted-foreground" htmlFor="wb-paste-url">
                          Paste WatchBase watch page URL
                        </label>
                        <Input
                          id="wb-paste-url"
                          className="font-mono text-xs"
                          placeholder="https://watchbase.com/…"
                          value={pastedUrl}
                          onChange={(e) => setPastedUrl(e.target.value)}
                        />
                        <Button
                          type="button"
                          variant="secondary"
                          className="w-full"
                          disabled={importBusy || !pastedUrl.trim()}
                          onClick={() => runImport(pastedUrl)}
                        >
                          {importBusy ? "Importing…" : "Import from pasted URL"}
                        </Button>
                      </div>
                    </div>

                    <div className="rounded-lg border border-border p-4">
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        disabled={importBusy}
                        onClick={skipNoMatch}
                      >
                        No match — skip this watch
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">Preparing…</p>
              )}

              {importErr ? <p className="mt-3 text-sm text-red-400">{importErr}</p> : null}
              {lastOk ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Last import: {lastOk.price_points} price points ·{" "}
                  <a
                    href={lastOk.canonical_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline"
                  >
                    page
                  </a>
                </p>
              ) : null}
            </>
          )}
        </div>
      </div>
    </>
  );
}
