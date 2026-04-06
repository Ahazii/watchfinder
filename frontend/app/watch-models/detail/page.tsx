"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiUrl, fetchJson } from "@/lib/api";
import type { WatchModel } from "@/lib/types";
import { money } from "@/lib/format";
import {
  watchbaseGoogleSearchUrl,
  watchbaseGuessUrl,
} from "@/lib/watchbase";
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

  const wbGuess = watchbaseGuessUrl(brand, modelFamily, reference);
  const wbGoogle = watchbaseGoogleSearchUrl(brand, reference);

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
          <CardTitle>WatchBase &amp; external page</CardTitle>
          <CardDescription>
            <strong>Open WatchBase (guess)</strong> builds{" "}
            <code className="rounded bg-muted px-1">watchbase.com/brand-slug/family-slug/ref-with-dashes</code>
            . It only works when WatchBase uses the same slugs as our simple rules — otherwise use{" "}
            <strong>Search WatchBase (Google)</strong> or paste the page you find into{" "}
            <strong>Reference URL</strong> (example:{" "}
            <a
              className="text-primary underline-offset-4 hover:underline"
              href="https://watchbase.com/omega/seamaster-diver-300m/210-30-42-20-01-001"
              target="_blank"
              rel="noreferrer"
            >
              Omega 210.30.42.20.01.001
            </a>
            ). We do not scrape WatchBase; copy fields manually into specifications below. Respect their{" "}
            <a
              className="text-primary underline-offset-4 hover:underline"
              href="https://watchbase.com/"
              target="_blank"
              rel="noreferrer"
            >
              terms of use
            </a>
            .
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
