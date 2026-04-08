import type { WatchModel, WatchModelListResponse } from "@/lib/types";
import { fetchJson } from "@/lib/api";

/** Filters for GET /api/watch-models (AND between fields; `q` ORs across main text columns). */
export type WatchModelListFilters = {
  q?: string;
  brand?: string;
  reference?: string;
  model_family?: string;
  model_name?: string;
  caliber?: string;
  /** See OpenAPI `pricing` on GET /api/watch-models */
  pricing?: "all" | "has_signal" | "missing_signal" | "strict_needs" | "strict_ok";
  /** See OpenAPI `import_status` */
  import_status?: "all" | "unmatched" | "matched";
};

export function appendWatchModelListFilters(params: URLSearchParams, f: WatchModelListFilters): void {
  if (f.q?.trim()) params.set("q", f.q.trim());
  if (f.brand?.trim()) params.set("brand", f.brand.trim());
  if (f.reference?.trim()) params.set("reference", f.reference.trim());
  if (f.model_family?.trim()) params.set("model_family", f.model_family.trim());
  if (f.model_name?.trim()) params.set("model_name", f.model_name.trim());
  if (f.caliber?.trim()) params.set("caliber", f.caliber.trim());
  if (f.pricing && f.pricing !== "all") params.set("pricing", f.pricing);
  if (f.import_status && f.import_status !== "all") params.set("import_status", f.import_status);
}

/** U3: no reference URL or never WatchBase-imported. */
export function isUnmatchedU3(m: WatchModel): boolean {
  const noUrl = !(m.reference_url && m.reference_url.trim());
  const neverImported = !m.watchbase_imported_at;
  return noUrl || neverImported;
}

/** P3: no price history points or no manual low/high. */
export function lacksPricingP3(m: WatchModel): boolean {
  const pts = m.external_price_history?.points;
  const noHistory = !pts || pts.length === 0;
  const noManual = m.manual_price_low == null && m.manual_price_high == null;
  return noHistory || noManual;
}

export function buildWatchbaseSearchQuery(
  m: Pick<WatchModel, "brand" | "reference" | "model_family">,
): string {
  const parts = [m.brand, m.model_family, m.reference].map((x) => (x ?? "").trim()).filter(Boolean);
  return parts.join(" ").trim();
}

/** All pages for current list filters (used by catalog presets). */
export async function fetchAllWatchModels(filters: WatchModelListFilters): Promise<WatchModel[]> {
  const items: WatchModel[] = [];
  let skip = 0;
  const limit = 200;
  for (;;) {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    appendWatchModelListFilters(params, filters);
    const r = await fetchJson<WatchModelListResponse>(`/api/watch-models?${params}`);
    items.push(...r.items);
    if (r.items.length < limit || items.length >= r.total) break;
    skip += limit;
  }
  return items;
}

export function randomWatchbaseDelayMs(): number {
  return 1000 + Math.floor(Math.random() * 4000);
}

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** Stable batch order: lower row index first (current table), then by id. */
export function sortIdsForBatch(ids: Iterable<string>, rowOrderHint: Map<string, number>): string[] {
  const list = Array.from(ids);
  return list.sort((a, b) => {
    const ia = rowOrderHint.has(a) ? rowOrderHint.get(a)! : 1_000_000;
    const ib = rowOrderHint.has(b) ? rowOrderHint.get(b)! : 1_000_000;
    if (ia !== ib) return ia - ib;
    return a.localeCompare(b);
  });
}
