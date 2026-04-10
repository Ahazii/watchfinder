/**
 * Strip HTML-like fragments for safe display when upstream parsing returns tags or entities.
 */
export function plainTextFromMaybeHtml(raw: string | null | undefined): string {
  if (raw == null || raw === "") return "";
  let s = String(raw);
  s = s.replace(/<[^>]+>/g, " ");
  s = s
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
  return s.replace(/\s+/g, " ").trim();
}
