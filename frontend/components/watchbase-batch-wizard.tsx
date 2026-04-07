"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiUrl, fetchJson, mediaUrl } from "@/lib/api";
import type {
  WatchBaseImportResult,
  WatchModel,
  WatchbaseSearchResponse,
} from "@/lib/types";
import {
  buildWatchbaseSearchQuery,
  randomWatchbaseDelayMs,
  sleep,
} from "@/lib/watch-models-batch";
import { Button } from "@/components/ui/button";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Process in this order */
  orderedIds: string[];
  onImported: () => void;
};

export function WatchbaseBatchWizard({
  open,
  onClose,
  orderedIds,
  onImported,
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
  const [hits, setHits] = useState<WatchbaseSearchResponse["items"] | null>(null);
  const [searchErr, setSearchErr] = useState<string | null>(null);
  const [importErr, setImportErr] = useState<string | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [lastOk, setLastOk] = useState<WatchBaseImportResult | null>(null);

  const total = orderedIds.length;
  const done = stepIndex >= total;
  const currentId = !done ? orderedIds[stepIndex] : null;

  useEffect(() => {
    if (!open) {
      setStepIndex(0);
      setCurrentModel(null);
      setHits(null);
      setSearchErr(null);
      setImportErr(null);
      setLastOk(null);
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
      try {
        await sleep(randomWatchbaseDelayMs());
        if (cancelled) return;
        const m = await fetchJson<WatchModel>(`/api/watch-models/${currentId}`);
        if (cancelled) return;
        setCurrentModel(m);

        const q = buildWatchbaseSearchQuery(m);
        if (!q) {
          setHits([]);
          setSearchErr(null);
          setPhaseBusy(false);
          return;
        }
        await sleep(randomWatchbaseDelayMs());
        if (cancelled) return;
        const res = await fetchJson<WatchbaseSearchResponse>(
          `/api/watchbase/search?q=${encodeURIComponent(q)}`,
        );
        if (!cancelled) setHits(res.items);
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

  if (!open) return null;

  const ourImage = currentModel?.image_urls?.find((u) => typeof u === "string" && u.trim())?.trim();

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
              Drag header to move. Click the dimmed page behind to use the list; click this panel to continue.
              Random 1–5 s delay between WatchBase calls. Escape closes (progress is not saved).
            </p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        <div className="max-h-[min(85vh,900px)] overflow-y-auto p-4">
          {done ? (
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
                  </div>

                  <div className="rounded-lg border border-border p-4">
                    <p className="text-sm font-semibold text-foreground">WatchBase matches</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Query: <span className="font-mono">{buildWatchbaseSearchQuery(currentModel) || "—"}</span>
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

                    <div className="mt-4 border-t border-border pt-4">
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
