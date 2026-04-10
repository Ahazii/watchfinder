import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { plainTextFromMaybeHtml } from "@/lib/plain-text";

type Props = {
  href: string;
  title: string;
  imageUrl?: string | null;
  priceHint?: string | null;
  openLabel?: string;
  className?: string;
};

export function MarketMatchRow({
  href,
  title,
  imageUrl,
  priceHint,
  openLabel = "Open page",
  className,
}: Props) {
  const label = plainTextFromMaybeHtml(title) || "Listing";

  return (
    <div
      className={cn(
        "flex gap-3 rounded-md border border-border bg-muted/10 p-2 text-left",
        className,
      )}
    >
      <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded border border-border bg-muted/40">
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- remote market CDN
          <img
            src={imageUrl}
            alt=""
            className="max-h-full max-w-full object-contain"
            referrerPolicy="no-referrer"
          />
        ) : (
          <span className="px-1 text-center text-[10px] leading-tight text-muted-foreground">
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
