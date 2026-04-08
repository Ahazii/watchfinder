"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { apiUrl } from "@/lib/api";
import type { EverywatchDebugResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

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
              <strong>GET …/search, /for-sale, /watch-search → 404</strong> — those URLs are not real server routes on
              everywatch.com (the site is a Next.js app; search runs in the browser). Our list is only a probe; 404 here
              is expected, not a failure of login.
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
              placeholder="Rolex Submariner 126610"
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
              placeholder="https://everywatch.com/..."
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
                <strong>analysis</strong> includes <code className="rounded bg-muted px-1">og_tags</code>,{" "}
                <code className="rounded bg-muted px-1">json_ld_previews</code>,{" "}
                <code className="rounded bg-muted px-1">parsed_listing_hits_sample</code> (current importer), etc.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {result.fetches.map((f, i) => (
                <div key={`${f.url}-${i}`} className="rounded-lg border border-border p-3">
                  <p className="break-all font-mono text-xs text-muted-foreground">{f.url}</p>
                  <p className="mt-1 text-sm">
                    HTTP {f.status_code ?? "—"} · html: {f.html_received ? "yes" : "no"}
                    {f.error ? (
                      <span className="ml-2 text-red-400">· {f.error}</span>
                    ) : null}
                  </p>
                  {f.analysis ? (
                    <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-md bg-muted/15 p-2 font-mono text-[11px]">
                      {JSON.stringify(f.analysis, null, 2)}
                    </pre>
                  ) : null}
                </div>
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
