import type { Metadata } from "next";
import type { ReactNode } from "react";
import { DM_Sans } from "next/font/google";
import "./globals.css";
import { SiteNav } from "@/components/site-nav";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "WatchFinder",
  description: "eBay watch sourcing — repair & resale signals",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" className={dmSans.variable}>
      <body className={`min-h-screen font-sans ${dmSans.className}`}>
        <div className="border-b border-border bg-card/40 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <a href="/" className="text-lg font-semibold tracking-tight text-primary">
              WatchFinder
            </a>
            <SiteNav />
          </div>
        </div>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
