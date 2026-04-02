"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiUrl, fetchJson } from "@/lib/api";
import type { WatchModel } from "@/lib/types";
import { money } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

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
    };
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

  return (
    <div className="space-y-6">
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
          <CardTitle>Media &amp; notes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
            Manual range is yours. Observed min/max are derived from linked listings and compatible
            sale records (refreshed on save and when listings analyze).
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium" htmlFor="ml">
              Manual low
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
              Manual high
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
            <p className="mt-1 tabular-nums text-muted-foreground">
              {money(observedLow)} – {money(observedHigh)}
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
