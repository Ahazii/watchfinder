/* eslint-disable @next/next/no-img-element -- eBay CDN URLs; static export avoids next/image remote config */
import { mediaUrl } from "@/lib/api";

/** First image URL from eBay ingest, cached `/api/media/...`, or manual catalog URLs. */

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
  const largeThumb =
    /\bh-(2[4-9]|[3-9]\d)\b/.test(sizeClass) || sizeClass.includes("h-56");
  const objectFit = largeThumb ? "object-contain" : "object-cover";
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
      src={mediaUrl(u.trim())}
      alt={alt}
      className={`shrink-0 rounded bg-muted ${objectFit} ${sizeClass}`}
      loading="lazy"
      referrerPolicy="no-referrer"
    />
  );
}
