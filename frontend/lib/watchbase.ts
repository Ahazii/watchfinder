/**
 * Heuristic WatchBase URLs. Paths use slugified brand + family + ref with dots → dashes.
 * May 404 if the family slug does not match WatchBase’s URL (paste the real page into **reference URL** on the model).
 * @see https://watchbase.com/omega/seamaster-diver-300m/210-30-42-20-01-001
 */

export function slugifyWatchbaseSegment(s: string): string {
  const t = s
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return t || "watch";
}

export function watchbaseGuessUrl(
  brand: string,
  modelFamily: string,
  reference: string,
): string | null {
  const ref = reference.trim();
  const b = brand.trim();
  const f = modelFamily.trim();
  if (!b || !f || !ref) return null;
  const refSlug = ref.replace(/\./g, "-");
  return `https://watchbase.com/${slugifyWatchbaseSegment(b)}/${slugifyWatchbaseSegment(f)}/${refSlug}`;
}

export function watchbaseGoogleSearchUrl(brand: string, reference: string): string | null {
  const ref = reference.trim();
  if (!ref) return null;
  const b = brand.trim();
  const q = b ? `site:watchbase.com ${b} ${ref}` : `site:watchbase.com ${ref}`;
  return `https://www.google.com/search?q=${encodeURIComponent(q)}`;
}
