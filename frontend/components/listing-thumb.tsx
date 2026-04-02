/* eslint-disable @next/next/no-img-element -- eBay CDN URLs; static export avoids next/image remote config */
/** First image URL from eBay ingest or manual catalog URLs; plain img for static export. */

export function ListingThumb({
  urls,
  alt = "",
  sizeClass = "h-10 w-10",
}: {
  urls?: string[] | null;
  alt?: string;
  sizeClass?: string;
}) {
  const u = urls?.find((x) => typeof x === "string" && x.trim().length > 0);
  if (!u) {
    return (
      <span
        className={`inline-block shrink-0 rounded bg-muted ${sizeClass}`}
        aria-hidden
      />
    );
  }
  return (
    <img
      src={u.trim()}
      alt={alt}
      className={`shrink-0 rounded object-cover bg-muted ${sizeClass}`}
      loading="lazy"
      referrerPolicy="no-referrer"
    />
  );
}
