/** Default when API omits currency (watch catalog bounds are stored as GBP). */
const FALLBACK_CURRENCY = "GBP";

function normalizeCurrency(currency?: string | null): string {
  const c = (currency && String(currency).trim().toUpperCase()) || "";
  if (c.length === 3 && /^[A-Z]{3}$/.test(c)) {
    return c;
  }
  return FALLBACK_CURRENCY;
}

function parseMoneyNumber(value: string | number): number {
  if (typeof value === "number") return value;
  const t = String(value).replace(/,/g, "").trim();
  return parseFloat(t);
}

/**
 * Format a monetary amount with the correct symbol (via Intl).
 * When `currency` is missing or invalid, **GBP** is assumed (watch database convention).
 */
export function money(
  value: string | number | null | undefined,
  currency?: string | null,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = parseMoneyNumber(value as string | number);
  if (Number.isNaN(n)) return String(value);
  const code = normalizeCurrency(currency);
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return code === "GBP" ? `£${n.toFixed(2)}` : `${code} ${n.toFixed(2)}`;
  }
}

/** Suffix for numeric inputs, e.g. ` (£)` or ` ($)` from the listing currency. */
export function currencyInputLabelSuffix(currency?: string | null): string {
  const code = normalizeCurrency(currency);
  try {
    const parts = new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).formatToParts(1);
    const sym = parts.find((p) => p.type === "currency")?.value;
    return sym ? ` (${sym})` : ` (${code})`;
  } catch {
    return ` (${code})`;
  }
}

export function pct(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(n)) return String(value);
  return `${(n * 100).toFixed(1)}%`;
}

export function dateShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
