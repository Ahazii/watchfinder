import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { plainTextFromMaybeHtml } from "@/lib/plain-text";

type Props = {
  href: string;
  title: string;
  imageUrl?: string | null;
  priceHint?: string | null;
  openLabel?: string;
  /** Thumbnail box size (default: extra large). */
  imageSize?: "lg" | "xl";
  className?: string;
};

export function MarketMatchRow({
  href,
  title,
  imageUrl,
  priceHint,
  openLabel = "Open page",
  imageSize = "xl",
  className,
}: Props) {
  const label = plainTextFromMaybeHtml(title) || "Listing";
  const thumbBox =
    imageSize === "xl"
      ? "h-52 w-52 min-h-[13rem] min-w-[13rem] sm:h-60 sm:w-60 sm:min-h-[15rem] sm:min-w-[15rem]"
      : "h-44 w-44 min-h-[11rem] min-w-[11rem] sm:h-52 sm:w-52 sm:min-h-[13rem] sm:min-w-[13rem]";

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-md border border-border bg-muted/10 p-3 text-left sm:flex-row sm:items-start",
        className,
      )}
    >
      <div
        className={cn(
          "flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-muted/40",
          thumbBox,
        )}
      >
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- remote market CDN
          <img
            src={imageUrl}
            alt=""
            className="h-full w-full object-contain p-1"
            referrerPolicy="no-referrer"
          />
        ) : (
          <span className="px-2 text-center text-xs leading-tight text-muted-foreground">
            No image
          </span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="line-clamp-3 text-sm font-medium leading-snug">{label}</p>
        {priceHint ? (
          <p className="mt-0.5 text-xs text-muted-foreground">{priceHint}</p>
        ) : null}
        <div className="mt-2">
          <Button variant="outline" size="sm" asChild>
            <a href={href} target="_blank" rel="noopener noreferrer">
              {openLabel}
            </a>
          </Button>
        </div>
      </div>
    </div>
  );
}
