"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/listings/", label: "Listings" },
  { href: "/candidates/", label: "Candidates" },
  { href: "/settings/", label: "Settings" },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-wrap items-center gap-1 text-sm">
      {links.map(({ href, label }) => {
        const active =
          href === "/"
            ? pathname === "/" || pathname === ""
            : pathname.startsWith(href.replace(/\/$/, ""));
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "rounded-md px-3 py-1.5 transition-colors",
              active
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
