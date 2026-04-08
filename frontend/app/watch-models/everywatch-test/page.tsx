"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { apiUrl } from "@/lib/api";
import type { EverywatchDebugFetchRow, EverywatchDebugResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type EwListingHit = {
  url?: string;
  label?: string;
  amount?: string | null;
  currency?: string | null;
};

type EwDetailPreview = {
  url?: string;
  label?: string;
  amount?: string | null;
  currency?: string | null;
  image_url?: string | null;
  specs?: Record<string, string>;
  price_analysis?: { title?: string; raw_text?: string; gbp_amounts?: string[] }[];
};

function EverywatchFetchBlock({ f }: { f: EverywatchDebugFetchRow }) {
  const analysis = f.analysis;
  const hits = (analysis?.parsed_listing_hits_sample as EwListingHit[] | undefined) ?? [];
  const detail = analysis?.detail_import_preview as EwDetailPreview | null | undefined;
  const hasSpecs = detail?.specs && Object.keys(detail.specs).length > 0;
  const copyUrl = (u: string) => {
    void navigator.clipboard?.writeText(u);
  };

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="break-all font-mono text-xs text-muted-foreground">{f.url}</p>
      <p className="mt-1 text-sm">
        HTTP {f.status_code ?? "—"} · html: {f.html_received ? "yes" : "no"}
        {f.error ? <span className="ml-2 text-red-400">· {f.error}</span> : null}
      </p>

      {hits.length > 0 ? (
        <div className="mt-3 space-y-2">
          <p className="text-sm font-medium">Parsed watch links ({hits.length} sample)</p>
          <p className="text-xs text-muted-foreground">
            Open a row to confirm the match, then paste that URL into <strong>Extra absolute URLs</strong> or save it as{" "}
            <strong>Everywatch watch URL</strong> on the model detail page.
          </p>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full min-w-[520px] text-left text-xs">
              <thead className="border-b border-border bg-muted/30 text-muted-foreground">
                <tr>
                  <th className="p-2 font-medium">Label</th>
                  <th className="p-2 font-medium">Price hint</th>
                  <th className="p-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {hits.map((h, j) => {
                  const u = (h.url || "").trim();
                  const hint =
                    h.amount && h.currency ? `${h.amount} ${h.currency}` : "—";
                  return (
                    <tr key={`${u}-${j}`} className="border-b border-border/60 last:border-0">
                      <td className="max-w-[280px] p-2 align-top">{(h.label || "").slice(0, 200)}</td>
                      <td className="whitespace-nowrap p-2 align-top">{hint}</td>
                      <td className="p-2 align-top">
                        <div className="flex flex-wrap gap-1">
                          {u ? (
                            <>
                              <Button variant="outline" size="sm" className="h-7 px-2 text-[11px]" asChild>
                                <a href={u} target="_blank" rel="noreferrer">
                                  Open
                                </a>
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-7 px-2 text-[11px]"
                                onClick={() => copyUrl(u)}
                              >
                                Copy URL
                              </Button>
                            </>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {detail && (detail.url || detail.image_url || hasSpecs || (detail.price_analysis?.length ?? 0) > 0) ? (
        <div className="mt-4 space-y-2 rounded-md border border-emerald-900/40 bg-emerald-950/15 p-3">
          <p className="text-sm font-medium text-emerald-200/90">Detail page import preview</p>
          {detail.image_url ? (
            <div className="flex max-w-xs flex-col gap-1">
              <span className="text-[11px] text-muted-foreground">Hero image (parsed)</span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={detail.image_url}
                alt={detail.label || "Everywatch"}
                className="max-h-48 rounded border border-border object-contain"
              />
            </div>
          ) : null}
          {hasSpecs ? (
            <dl className="grid max-h-56 grid-cols-1 gap-x-4 gap-y-1 overflow-y-auto text-xs sm:grid-cols-2">
              {Object.entries(detail.specs!).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <dt className="shrink-0 font-medium text-muted-foreground">{k}</dt>
                  <dd className="break-words">{v}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {(detail.price_analysis?.length ?? 0) > 0 ? (
            <ul className="space-y-1 text-xs">
              {detail.price_analysis!.map((row, idx) => (
                <li key={idx}>
                  <span className="font-medium">{row.title || "—"}</span>
                  {row.gbp_amounts?.length ? (
                    <span className="ml-2 text-muted-foreground">
                      GBP: {row.gbp_amounts.join(", ")}
                    </span>
                  ) : (
                    <span className="ml-2 text-muted-foreground">{row.raw_text}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : null}
          {detail.url ? (
            <Button variant="outline" size="sm" className="h-7 text-xs" asChild>
              <a href={detail.url} target="_blank" rel="noreferrer">
                Open detail page
              </a>
            </Button>
          ) : null}
        </div>
      ) : null}

      {analysis ? (
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-md bg-muted/15 p-2 font-mono text-[11px]">
          {JSON.stringify(analysis, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

export default function EverywatchTestPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
      <EverywatchTestBody />
    </Suspense>
  );
}

function EverywatchTestBody() {
  const sp = useSearchParams();
  const idFromQuery = sp.get("id")?.trim() || "";

  const [modelId, setModelId] = useState(idFromQuery);
  const [extraUrls, setExtraUrls] = useState("");
  const [searchQueries, setSearchQueries] = useState("");
  const [cookieHeader, setCookieHeader] = useState("");
  const [useSavedLogin, setUseSavedLogin] = useState(true);
  const [overrideEmail, setOverrideEmail] = useState("");
  const [overridePassword, setOverridePassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<EverywatchDebugResponse | null>(null);

  const run = () => {
    setBusy(true);
    setErr(null);
    setResult(null);
    const extra = extraUrls
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    const queries = searchQueries
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    const body: Record<string, unknown> = {
      extra_urls: extra,
      search_queries: queries,
    };
    if (modelId.trim()) body.watch_model_id = modelId.trim();
    const ch = cookieHeader.trim();
    if (ch) body.cookie_header = ch;
    else {
      body.use_saved_everywatch_login = useSavedLogin;
      if (overrideEmail.trim()) body.override_login_email = overrideEmail.trim();
      if (overridePassword) body.override_login_password = overridePassword;
    }

    fetch(apiUrl("/api/everywatch/debug"), {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<EverywatchDebugResponse>;
      })
      .then(setResult)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Everywatch import tester</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Debug tool: fetches HTML from{" "}
          <a
            className="text-primary underline-offset-4 hover:underline"
            href="https://everywatch.com/"
            target="_blank"
            rel="noreferrer"
          >
            Everywatch
          </a>{" "}
          and shows parsed structure so you can plan field mapping. Nothing is saved to your catalog from this page.
          Comply with Everywatch terms; keep request volume low.
        </p>
      </div>

      <Card className="border-amber-900/50 bg-amber-950/20">
        <CardHeader>
          <CardTitle className="text-base">Security</CardTitle>
          <CardDescription>
            Email/password are stored in <strong>Settings</strong> as plaintext for this self-hosted flow. Optional{" "}
            <strong>Cookie</strong> below overrides login for one request. Use a strong unique password and restrict DB
            access.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reading your server logs</CardTitle>
          <CardDescription className="space-y-2 text-sm leading-relaxed">
            <p>
              <strong>POST …/api/Auth/Login 200</strong> — credentials were accepted; the app then adds session cookies
              (and a bearer token if present) to the following GETs.
            </p>
            <p>
              <strong>GET …/omega/1931 404</strong> — Everywatch has no public page at that guessed path (reference{" "}
              <code className="rounded bg-muted px-1">1931</code> is often a year, not their internal slug). Vintage
              pieces rarely match <code className="rounded bg-muted px-1">/brand/&lt;alnum-ref&gt;</code>.
            </p>
            <p>
              <strong>GET …/watch-listing?query=…</strong> — real HTML search results (server-rendered). Extra search lines
              now try this <em>first</em>, then legacy <code className="rounded bg-muted px-1">/search</code> probes that
              often <strong>404</strong>.
            </p>
            <p>
              <strong>GET …/?q=… 200</strong> — you get the <em>homepage HTML shell</em>. Listing cards usually load via
              JavaScript / internal APIs after page load, so <code className="rounded bg-muted px-1">parsed_listing_hits</code>{" "}
              may stay empty until we call the same JSON endpoints the site uses (use DevTools → Network on a manual search
              to find them, then paste those URLs under <strong>Extra absolute URLs</strong>).
            </p>
            <p>
              When a direct <code className="rounded bg-muted px-1">…/watch-1234567</code> URL returns <strong>200</strong>, save
              it on the watch model under <strong>Everywatch watch URL</strong> (detail page) so{" "}
              <strong>Refresh market snapshots</strong> and <strong>Find on markets</strong> use it in production without
              re-pasting.
            </p>
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Request</CardTitle>
          <CardDescription>
            With a <strong>watch model id</strong>, the server builds the same <code className="rounded bg-muted px-1">/brand/ref</code> URLs
            as production plus several guessed search URLs (home search uses{" "}
            <code className="rounded bg-muted px-1">#ew-search-home</code> — the site may route via client-side API; these GETs are probes).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border"
              checked={useSavedLogin}
              disabled={Boolean(cookieHeader.trim())}
              onChange={(e) => setUseSavedLogin(e.target.checked)}
            />
            Use saved Everywatch login from Settings (recommended)
          </label>
          {!cookieHeader.trim() ? (
            <div className="grid gap-3 rounded-md border border-border/60 bg-muted/10 p-3 sm:grid-cols-2">
              <div className="sm:col-span-2 text-xs text-muted-foreground">
                Optional one-shot overrides (leave blank to use Settings only).
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="ew-ov-email">
                  Override email
                </label>
                <Input
                  id="ew-ov-email"
                  type="email"
                  autoComplete="off"
                  value={overrideEmail}
                  onChange={(e) => setOverrideEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="ew-ov-pass">
                  Override password
                </label>
                <Input
                  id="ew-ov-pass"
                  type="password"
                  autoComplete="new-password"
                  value={overridePassword}
                  onChange={(e) => setOverridePassword(e.target.value)}
                />
              </div>
            </div>
          ) : null}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="ew-mid">
              Watch model ID (optional)
            </label>
            <Input
              id="ew-mid"
              placeholder="uuid from watch database detail URL"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="ew-sq">
              Extra search lines (optional, one query per line)
            </label>
            <textarea
              id="ew-sq"
              className="min-h-[72px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder={'e.g. Omega 166.085 → /watch-listing?query=…'}
              value={searchQueries}
              onChange={(e) => setSearchQueries(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="ew-url">
              Extra absolute URLs (optional, one per line)
            </label>
            <textarea
              id="ew-url"
              className="min-h-[72px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="https://everywatch.com/watch-listing?… or …/omega/de-ville/watch-123"
              value={extraUrls}
              onChange={(e) => setExtraUrls(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="ew-cookie">
              Cookie header (optional — skips API login if non-empty)
            </label>
            <textarea
              id="ew-cookie"
              className="min-h-[56px] w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs"
              placeholder="Paste Cookie header from browser DevTools if API login is not enough"
              value={cookieHeader}
              onChange={(e) => setCookieHeader(e.target.value)}
              autoComplete="off"
            />
          </div>
          <Button type="button" disabled={busy} onClick={() => run()}>
            {busy ? "Fetching…" : "Run debug fetch"}
          </Button>
          {err ? <p className="text-sm text-red-400">{err}</p> : null}
        </CardContent>
      </Card>

      {result ? (
        <>
          {result.login_attempt && Object.keys(result.login_attempt).length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Login attempt (server)</CardTitle>
                <CardDescription>
                  <code className="rounded bg-muted px-1">POST /api/Auth/Login</code> on api.everywatch.com — no secrets
                  returned.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-md border border-border bg-muted/15 p-3 font-mono text-xs">
                  {JSON.stringify(result.login_attempt, null, 2)}
                </pre>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>URLs attempted</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
                {result.urls_attempted.map((u) => (
                  <li key={u} className="break-all">
                    <a className="text-primary hover:underline" href={u} target="_blank" rel="noreferrer">
                      {u}
                    </a>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Production snapshot helper (collect_everywatch_snapshot)</CardTitle>
              <CardDescription>Same logic as automatic market snapshots — for comparison.</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-md border border-border bg-muted/20 p-3 font-mono text-xs">
                {JSON.stringify(result.collect_everywatch_snapshot, null, 2)}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Per-URL results</CardTitle>
              <CardDescription>
                Listing pages expose <code className="rounded bg-muted px-1">parsed_listing_hits_sample</code> as a table;
                watch detail pages add <code className="rounded bg-muted px-1">detail_import_preview</code> (specs,
                hero image, GBP price rows). Raw <code className="rounded bg-muted px-1">analysis</code> JSON is below
                each block.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {result.fetches.map((f, i) => (
                <EverywatchFetchBlock key={`${f.url}-${i}`} f={f} />
              ))}
            </CardContent>
          </Card>
        </>
      ) : null}

      <p className="text-sm text-muted-foreground">
        <Link href="/watch-models/" className="text-primary hover:underline">
          ← Watch database
        </Link>
        {modelId.trim() ? (
          <>
            {" · "}
            <Link
              href={`/watch-models/detail/?id=${encodeURIComponent(modelId.trim())}`}
              className="text-primary hover:underline"
            >
              Model detail
            </Link>
          </>
        ) : null}
      </p>
    </div>
  );
}
